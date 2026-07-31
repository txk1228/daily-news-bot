"""
每日科技新闻推送机器人

通过公开 RSS 按自定义主题拉取资讯，签名后推送到飞书群。
用法:
  python scripts/news_bot.py --once
  python scripts/news_bot.py --once --topics "AI大模型,具身智能,每日财经热点"
  python scripts/news_bot.py --schedule --topics "量子计算,机器人"
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import logging
import os
import re
import sys
import time
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import feedparser
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """从项目根目录加载 .env（不覆盖已有环境变量）。"""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as e:
        logger.warning("读取 .env 失败: %s", e)


_load_dotenv()

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "").strip().lstrip("\ufeff")
FEISHU_SECRET = os.getenv("FEISHU_SECRET", "").strip().lstrip("\ufeff")

KEYWORDS = ["小可每日资讯", "自动驾驶推送"]

DEFAULT_TOPICS = ("AI大模型", "具身智能", "每日财经热点")
MIN_TOPICS = 1
MAX_TOPICS = 5

# 本地定时默认（可被 .env 的 PUSH_HOUR / PUSH_MINUTE 覆盖）
DEFAULT_PUSH_HOUR = 7
DEFAULT_PUSH_MINUTE = 30


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("环境变量 %s=%r 非法，使用默认 %d", name, raw, default)
        return default


PUSH_HOUR = _env_int("PUSH_HOUR", DEFAULT_PUSH_HOUR)
PUSH_MINUTE = _env_int("PUSH_MINUTE", DEFAULT_PUSH_MINUTE)
if not (0 <= PUSH_HOUR <= 23 and 0 <= PUSH_MINUTE <= 59):
    logger.warning(
        "PUSH_HOUR/PUSH_MINUTE 超出范围 (%d:%02d)，回退到 %d:%02d",
        PUSH_HOUR,
        PUSH_MINUTE,
        DEFAULT_PUSH_HOUR,
        DEFAULT_PUSH_MINUTE,
    )
    PUSH_HOUR = DEFAULT_PUSH_HOUR
    PUSH_MINUTE = DEFAULT_PUSH_MINUTE

RSS_COUNT = 3
REQUEST_TIMEOUT = 15
FETCH_RETRIES = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# 国内可访问的科技 RSS（通用回退）
FALLBACK_FEEDS = (
    "https://www.ithome.com/rss/",
    "https://36kr.com/feed",
    "https://www.solidot.org/index.rss",
)

# 特定主题优先源（专业站点 RSS，避免 Google 泛搜出地方杂讯）
TOPIC_PRIMARY_FEEDS: dict[str, tuple[str, ...]] = {
    "每日财经热点": (
        "https://rss.huxiu.com/",
        "https://36kr.com/feed",
    ),
}

# Google News 检索词（不填则直接用主题名）
TOPIC_SEARCH_QUERIES: dict[str, str] = {
    "每日财经热点": (
        "虎嗅 OR 华尔街见闻 OR 财联社 OR 第一财经 OR 界面新闻 OR 经济观察报"
    ),
    "具身智能": "具身智能 OR 人形机器人 OR 优必选 OR 智元 OR 宇树",
    "AI大模型": "AI大模型 OR 大模型 OR DeepSeek OR OpenAI OR Kimi",
}

# 主题同义词：国内综合源标题很少出现完整主题词，需放宽过滤
TOPIC_SYNONYMS: dict[str, tuple[str, ...]] = {
    "AI大模型": (
        "AI大模型",
        "大模型",
        "人工智能",
        "生成式",
        "ChatGPT",
        "OpenAI",
        "Claude",
        "Gemini",
        "Kimi",
        "DeepSeek",
        "通义",
        "文心",
        "智谱",
        "Grok",
        "LLM",
        "AIGC",
    ),
    "具身智能": (
        "具身智能",
        "人形机器人",
        "具身",
        "灵巧手",
        "四足机器人",
        "工业机器人",
        "Figure",
        "优必选",
        "智元",
        "宇树",
        "Tesla Bot",
        "Optimus",
        "机器人公司",
    ),
    "每日财经热点": (
        "每日财经热点",
        "财经",
        "商业",
        "消费",
        "融资",
        "IPO",
        "财报",
        "股市",
        "A股",
        "港股",
        "美股",
        "央行",
        "美联储",
        "降息",
        "加息",
        "通胀",
        "虎嗅",
        "华尔街见闻",
        "财联社",
    ),
}


def validate_config() -> None:
    """校验飞书环境变量，缺失则明确报错。"""
    missing = []
    if not FEISHU_WEBHOOK_URL:
        missing.append("FEISHU_WEBHOOK_URL")
    if not FEISHU_SECRET:
        missing.append("FEISHU_SECRET")
    if missing:
        logger.error(
            "缺少必要环境变量: %s。请运行 python scripts/setup_bot.py 或参考 .env.example。",
            ", ".join(missing),
        )
        sys.exit(1)


def parse_topics(raw: str | None) -> list[str]:
    """解析逗号分隔主题。优先：参数 > 环境变量 TOPICS > 代码默认。"""
    if raw is None or not str(raw).strip():
        env_topics = os.getenv("TOPICS", "").strip()
        if env_topics:
            raw = env_topics
        else:
            return list(DEFAULT_TOPICS)

    topics: list[str] = []
    seen: set[str] = set()
    for part in str(raw).split(","):
        topic = part.strip()
        if not topic:
            continue
        key = topic.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)

    if not (MIN_TOPICS <= len(topics) <= MAX_TOPICS):
        logger.error(
            "主题数量须为 %d–%d 个（英文逗号分隔），当前解析到 %d 个: %s",
            MIN_TOPICS,
            MAX_TOPICS,
            len(topics),
            topics or "(空)",
        )
        sys.exit(1)
    return topics


def topic_keywords(topic: str) -> tuple[str, ...]:
    """从主题字符串拆出回退过滤用关键词，并合并已知同义词。"""
    parts = re.split(r"[\s/|]+|(?:\s+OR\s+)", topic, flags=re.IGNORECASE)
    keywords = [p.strip() for p in parts if p and p.strip()]
    if topic not in keywords:
        keywords.insert(0, topic)
    keywords.extend(TOPIC_SYNONYMS.get(topic, ()))
    # 去重保序
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        key = kw.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(kw)
    return tuple(unique)


def google_news_rss_url(query: str) -> str:
    encoded = quote_plus(query)
    return (
        "https://news.google.com/rss/search"
        f"?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_snippet(snippet: str) -> str:
    """清理摘要：去掉发布时间、阅读量、来源标签等冗余信息。"""
    if not snippet:
        return ""

    replacements = [
        (r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?", " "),
        (r"\d{1,2}:\d{2}(:\d{2})?", " "),
        (r"\d+\s*[小时分钟秒天前]+", " "),
        (r"发表于\s*", " "),
        (r"来源[：:]\s*\S+", " "),
        (r"作者[：:]\s*\S+", " "),
        (r"\d+\s*阅读", ""),
        (r"阅读\s*\d+", ""),
        (r"编辑[：:]\s*\S+", " "),
        (r"发布于\s*\S+", " "),
    ]
    for pattern, replacement in replacements:
        snippet = re.sub(pattern, replacement, snippet)

    snippet = re.sub(r"[。，；：、,\.;:\s]+", " ", snippet).strip()
    if len(snippet) > 55:
        snippet = snippet[:52] + "..."
    return snippet


def _fetch_feed(url: str, retries: int = FETCH_RETRIES) -> Any | None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                },
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if getattr(feed, "bozo", False) and not feed.entries:
                logger.warning(
                    "RSS 解析异常 [%s]: %s",
                    url,
                    getattr(feed, "bozo_exception", ""),
                )
                return None
            return feed
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
    logger.warning("拉取 RSS 失败 [%s]: %s", url, last_error)
    return None


def _entry_to_item(entry: Any, default_source: str = "") -> dict[str, str]:
    title = strip_html(getattr(entry, "title", "") or "无标题")
    source = default_source
    if hasattr(entry, "source") and getattr(entry.source, "title", None):
        source = entry.source.title
    elif getattr(entry, "author", None):
        source = str(entry.author)
    snippet = strip_html(
        getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    )
    return {
        "title": title,
        "source": source or "未知来源",
        "url": getattr(entry, "link", "") or "",
        "snippet": snippet[:80],
    }


def _match_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    lower = text.lower()
    for kw in keywords:
        if kw.lower() in lower:
            return True
    return False


_fallback_feed_cache: dict[str, Any | None] = {}

# Google / 杂讯标题黑名单（地方站、个人页等）
_TITLE_BLOCKLIST = (
    "个人中心",
    "的个人主页",
    "登录",
    "注册",
    "甘肃日报",
    "兰州晚报",
    "新甘肃",
)


def _is_junk_item(item: dict[str, str]) -> bool:
    blob = f"{item.get('title', '')} {item.get('source', '')} {item.get('url', '')}"
    return any(bad in blob for bad in _TITLE_BLOCKLIST)


def _load_feeds(urls: tuple[str, ...]) -> list[tuple[str, Any]]:
    """按 URL 列表加载 RSS，同一次任务内复用缓存。"""
    loaded: list[tuple[str, Any]] = []
    for feed_url in urls:
        if feed_url not in _fallback_feed_cache:
            _fallback_feed_cache[feed_url] = _fetch_feed(feed_url)
        feed = _fallback_feed_cache[feed_url]
        if feed and feed.entries:
            loaded.append((feed_url, feed))
    return loaded


def _collect_from_feeds(
    feed_pairs: list[tuple[str, Any]],
    *,
    keywords: tuple[str, ...] | None,
    count: int,
    seen_titles: set[str],
) -> list[dict[str, str]]:
    """从已加载 feed 收集条目；keywords 为 None 时不过滤。"""
    results: list[dict[str, str]] = []
    for feed_url, feed in feed_pairs:
        feed_title = getattr(feed.feed, "title", "") or feed_url
        for entry in feed.entries:
            item = _entry_to_item(entry, default_source=str(feed_title))
            if _is_junk_item(item):
                continue
            if keywords is not None:
                blob = f"{item['title']} {item['snippet']}"
                if not _match_keywords(blob, keywords):
                    continue
            title_key = item["title"].strip().lower()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            results.append(item)
            if len(results) >= count:
                return results
    return results


def search_news_by_topic(topic: str, count: int = RSS_COUNT) -> list[dict[str, str]]:
    """按主题拉新闻：专业源优先，再 Google，最后通用国内 RSS。"""
    keywords = topic_keywords(topic)
    seen_titles: set[str] = set()
    results: list[dict[str, str]] = []

    # 1) 主题专属专业源（如财经 → 虎嗅）
    primary_urls = TOPIC_PRIMARY_FEEDS.get(topic)
    if primary_urls:
        # 虎嗅等专业源本身即垂类，不再强制关键词，避免误杀
        primary_items = _collect_from_feeds(
            _load_feeds(primary_urls),
            keywords=None,
            count=count,
            seen_titles=seen_titles,
        )
        results.extend(primary_items)
        if len(results) >= count:
            logger.info("「%s」经专业源获取到 %d 条", topic, len(results))
            return results[:count]
        logger.info(
            "「%s」专业源仅 %d 条，继续补充其他来源",
            topic,
            len(results),
        )

    # 2) Google News（可用主题定制检索词，避免泛搜出地方杂讯）
    query = TOPIC_SEARCH_QUERIES.get(topic, topic)
    google_url = google_news_rss_url(query)
    feed = _fetch_feed(google_url, retries=1)
    if feed and feed.entries:
        for entry in feed.entries:
            item = _entry_to_item(entry)
            if _is_junk_item(item):
                continue
            title_key = item["title"].strip().lower()
            if not title_key or title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            results.append(item)
            if len(results) >= count:
                break
        if len(results) >= count:
            logger.info("「%s」经 Google News 获取到 %d 条", topic, len(results))
            return results[:count]

    logger.info("「%s」改用国内通用 RSS 回退补充", topic)

    # 3) 通用国内 RSS + 同义词过滤
    more = _collect_from_feeds(
        _load_feeds(FALLBACK_FEEDS),
        keywords=keywords,
        count=count - len(results),
        seen_titles=seen_titles,
    )
    results.extend(more)
    logger.info("「%s」获取到 %d 条新闻", topic, len(results))
    return results[:count]


def generate_sign(secret: str, timestamp: str) -> str:
    """生成飞书签名。"""
    key = f"{timestamp}\n{secret}"
    return base64.b64encode(
        hmac.new(key.encode(), b"", hashlib.sha256).digest()
    ).decode("utf-8")


def send_with_sign(content: str) -> dict[str, Any]:
    """使用签名校验发送消息到飞书（timestamp/sign 放入请求体）。"""
    try:
        timestamp = str(int(time.time()))
        sign = generate_sign(FEISHU_SECRET, timestamp)
        payload = {
            "timestamp": timestamp,
            "sign": sign,
            "msg_type": "text",
            "content": {"text": content},
        }
        response = requests.post(
            FEISHU_WEBHOOK_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        result = response.json()
        logger.info("飞书响应: %s", result)
        return result
    except Exception as e:
        logger.error("发送失败: %s", e)
        return {"code": -1, "msg": str(e)}


def _format_item_line(item: dict[str, str], index: int) -> str:
    """格式化为「1）标题 [来源] 🔗 链接」。"""
    title = (
        item["title"]
        .replace("【", "")
        .replace("】", "")
        .strip()
    )
    title = re.sub(r"\s*[-|｜]\s*[^\s\-｜]{1,24}$", "", title).strip() or item["title"].strip()
    url = (item.get("url") or "").strip()
    source = (item.get("source") or "").strip()

    if "huxiu.com" in url:
        source_label = "虎嗅"
    elif "36kr.com" in url:
        source_label = "36氪"
    elif source and "个人" not in source and source not in title:
        source_label = source
    else:
        source_label = ""

    parts = [f"{index}）{title}"]
    if source_label:
        parts.append(f"[{source_label}]")
    if url:
        parts.append(f"🔗 {url}")
    return " ".join(parts)


def format_news_content(sections: list[tuple[str, list[dict[str, str]]]]) -> str:
    """按主题列表格式化新闻内容（各板块 1）2）3）分点）。"""
    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    topic_labels = [topic for topic, _ in sections]
    header_topics = " & ".join(topic_labels)
    lines = [
        f"🔔 小可每日资讯 | {header_topics}",
        f"📅 {today}",
    ]

    for topic, news in sections:
        lines.extend(["", f"📌 {topic}"])
        if news:
            for i, item in enumerate(news, start=1):
                lines.append(_format_item_line(item, i))
        else:
            lines.append("暂无最新资讯")

    lines.extend(
        [
            "",
            "✨ 每日积累，稳步精进～",
        ]
    )
    # 确保关键词出现在消息中（飞书自定义机器人关键词校验）
    _ = KEYWORDS
    return "\n".join(lines)


def job_news_push(topics: list[str]) -> int:
    """执行一次新闻推送。成功返回 0，失败返回非 0。"""
    _fallback_feed_cache.clear()
    logger.info("=" * 50)
    logger.info("开始执行新闻推送任务...")
    logger.info("主题: %s", ", ".join(topics))

    sections: list[tuple[str, list[dict[str, str]]]] = []
    any_news = False
    for topic in topics:
        logger.info("正在搜索「%s」新闻...", topic)
        news = search_news_by_topic(topic, count=RSS_COUNT)
        if news:
            any_news = True
        sections.append((topic, news))

    if not any_news:
        logger.error("未获取到任何新闻，任务终止")
        return 1

    content = format_news_content(sections)
    logger.info("正在发送到飞书...")
    result = send_with_sign(content)

    if result.get("code") == 0:
        logger.info("✅ 推送成功！")
        logger.info("=" * 50)
        return 0

    logger.error("❌ 推送失败: %s", result.get("msg"))
    logger.info("=" * 50)
    return 1


def run_schedule(topics: list[str]) -> None:
    """长驻：每天按 PUSH_HOUR:PUSH_MINUTE（北京时间）推送。"""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    webhook_preview = FEISHU_WEBHOOK_URL[:50] if FEISHU_WEBHOOK_URL else "(empty)"
    push_label = f"{PUSH_HOUR:02d}:{PUSH_MINUTE:02d}"
    logger.info("🚀 每日新闻推送机器人启动（定时模式）")
    logger.info("Webhook: %s...", webhook_preview)
    logger.info("签名校验: 已启用")
    logger.info("关键词: %s", KEYWORDS)
    logger.info("主题: %s", ", ".join(topics))

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        job_news_push,
        CronTrigger(hour=PUSH_HOUR, minute=PUSH_MINUTE, timezone="Asia/Shanghai"),
        args=[topics],
        id="daily_news_push",
        name="每日新闻推送",
    )
    logger.info("⏰ 定时任务已添加：每天北京时间 %s", push_label)
    logger.info("📡 等待执行中...")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ 机器人已停止")
        sys.exit(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="每日科技新闻推送机器人")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once",
        action="store_true",
        help="推送一次后退出（默认，适合 Cron / GitHub Actions）",
    )
    mode.add_argument(
        "--schedule",
        action="store_true",
        help=(
            f"长驻定时：每天北京时间 {PUSH_HOUR:02d}:{PUSH_MINUTE:02d} 推送"
            "（可由 .env 的 PUSH_HOUR/PUSH_MINUTE 配置）"
        ),
    )
    parser.add_argument(
        "--topics",
        type=str,
        default=None,
        help=(
            f'推送主题，英文逗号分隔，{MIN_TOPICS}–{MAX_TOPICS} 个；'
            f'优先 CLI，否则读环境变量 TOPICS，默认 "{",".join(DEFAULT_TOPICS)}"'
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_config()
    topics = parse_topics(args.topics)

    if args.schedule:
        run_schedule(topics)
        return

    # 默认与 --once：推送一次后退出
    exit_code = job_news_push(topics)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

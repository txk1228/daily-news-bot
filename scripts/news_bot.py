"""
每日科技新闻推送机器人 - 防风控版
关键词验证：小可每日资讯 / 自动驾驶推送
签名校验：已启用
"""
import os
import sys
import hmac
import hashlib
import base64
import time
import logging
import requests
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 飞书 Webhook 配置
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")
FEISHU_SECRET = os.getenv("FEISHU_SECRET")

# ✅ 关键词（必须包含在消息中才能通过风控）
KEYWORDS = ["小可每日资讯", "自动驾驶推送"]


def generate_sign(secret: str, timestamp: str) -> str:
    """
    生成飞书签名
    官方算法：使用 key = timestamp + "\\n" + secret，对空字符串进行 HMAC-SHA256 加密
    """
    key = f"{timestamp}\n{secret}"
    sign = base64.b64encode(
        hmac.new(key.encode(), b"", hashlib.sha256).digest()
    ).decode('utf-8')
    return sign


def send_with_sign(content: str) -> dict:
    """
    使用签名校验发送消息到飞书
    """
    try:
        # 生成签名
        timestamp = str(int(time.time()))
        sign = generate_sign(FEISHU_SECRET, timestamp)
        
        # 构建完整 URL（带签名参数）
        full_url = f"{FEISHU_WEBHOOK_URL}?timestamp={timestamp}&sign={sign}"
        
        # 构建消息体
        payload = {
            "msg_type": "text",
            "content": {
                "text": content
            }
        }
        
        # 发送请求
        response = requests.post(full_url, json=payload, timeout=30)
        result = response.json()
        
        logger.info(f"飞书响应: {result}")
        return result
        
    except Exception as e:
        logger.error(f"发送失败: {e}")
        return {"code": -1, "msg": str(e)}


def search_news(query: str, count: int = 3) -> list:
    """搜索新闻"""
    try:
        from coze_coding_dev_sdk import SearchClient
        from coze_coding_utils.runtime_ctx.context import new_context
        
        ctx = new_context(method="search.news")
        client = SearchClient(ctx=ctx)
        
        response = client.web_search(
            query=query,
            count=count,
            need_summary=True
        )
        
        if not response.web_items:
            return []
        
        results = []
        for item in response.web_items:
            results.append({
                "title": item.title or "无标题",
                "source": item.site_name or "未知来源",
                "url": item.url or "",
                "snippet": (item.snippet or item.summary or "")[:80]
            })
        return results
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return []


def format_news_content(ai_news: list, auto_news: list) -> str:
    """格式化新闻内容 - 精简清晰版"""
    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    
    lines = []
    
    # ==================== 头部 ====================
    lines.append("🔔 小可每日资讯 | 自动驾驶 & AI 专栏")
    lines.append(f"📅 {today}")
    lines.append("")
    
    # ==================== AI 大模型 ====================
    lines.append("🤖 AI 大模型")
    
    for item in ai_news:
        # 清理标题：去掉【】等多余符号
        title = item['title'].replace("【", "").replace("】", "").replace("：", " ").strip()
        # 清理摘要：去掉发布时间、阅读量等冗余信息
        snippet = clean_snippet(item['snippet'])
        lines.append(f"{title} {snippet}🔗 {item['url']}")
    
    lines.append("")
    
    # ==================== 自动驾驶 ====================
    lines.append("🚗 自动驾驶")
    
    for item in auto_news:
        # 清理标题：去掉【】等多余符号
        title = item['title'].replace("【", "").replace("】", "").replace("：", " ").strip()
        # 清理摘要：去掉发布时间、阅读量等冗余信息
        snippet = clean_snippet(item['snippet'])
        lines.append(f"{title} {snippet}🔗 {item['url']}")
    
    lines.append("")
    
    # ==================== 尾部 ====================
    lines.append("✨ 每日积累，稳步精进，为自动驾驶规控秋招蓄力～")
    
    return "\n".join(lines)


def clean_snippet(snippet: str) -> str:
    """清理摘要：去掉发布时间、阅读量、来源标签等冗余信息"""
    if not snippet:
        return ""
    
    import re
    
    # 批量替换清理
    replacements = [
        # 去掉日期时间：2026年05月09日、2026-05-09、08:30等
        (r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?', ' '),
        # 去掉时间：08:30:05、15:30等
        (r'\d{1,2}:\d{2}(:\d{2})?', ' '),
        # 去掉"XX小时/分钟/秒前"
        (r'\d+\s*[小时分钟秒天前]+', ' '),
        # 去掉"发表于 XX"
        (r'发表于\s*', ' '),
        # 去掉"来源：XXX"
        (r'来源[：:]\s*\S+', ' '),
        # 去掉"作者：XXX"
        (r'作者[：:]\s*\S+', ' '),
        # 去掉阅读量
        (r'\d+\s*阅读', ''),
        (r'阅读\s*\d+', ''),
        # 去掉"编辑：XXX"
        (r'编辑[：:]\s*\S+', ' '),
        # 去掉"发布于 XX"
        (r'发布于\s*\S+', ' '),
    ]
    
    for pattern, replacement in replacements:
        snippet = re.sub(pattern, replacement, snippet)
    
    # 清理多余标点和空格
    snippet = re.sub(r'[。，；：、,\.;:\s]+', ' ', snippet)
    snippet = snippet.strip()
    
    # 限制长度（核心内容50字左右）
    if len(snippet) > 55:
        snippet = snippet[:52] + "..."
    
    return snippet


def job_news_push():
    """定时推送任务"""
    logger.info("=" * 50)
    logger.info("开始执行新闻推送任务...")
    
    # 搜索新闻
    logger.info("正在搜索 AI 人工智能新闻...")
    ai_news = search_news("AI 人工智能 大模型", count=3)
    
    logger.info("正在搜索自动驾驶新闻...")
    auto_news = search_news("自动驾驶 智能驾驶", count=3)
    
    if not ai_news and not auto_news:
        logger.error("未获取到任何新闻，任务终止")
        return
    
    # 格式化消息
    content = format_news_content(ai_news, auto_news)
    
    # 发送（带签名校验）
    logger.info("正在发送到飞书...")
    result = send_with_sign(content)
    
    if result.get("code") == 0:
        logger.info("✅ 推送成功！")
    else:
        logger.error(f"❌ 推送失败: {result.get('msg')}")
    
    logger.info("=" * 50)


def main():
    """主函数"""
    logger.info("🚀 每日新闻推送机器人启动")
    logger.info(f"Webhook: {FEISHU_WEBHOOK_URL[:50]}...")
    logger.info(f"签名校验: 已启用")
    logger.info(f"关键词: {KEYWORDS}")
    
    # 创建调度器
    scheduler = BlockingScheduler(timezone="Asia/Shanghai")
    
    # 添加定时任务：每天北京时间 07:30
    scheduler.add_job(
        job_news_push,
        CronTrigger(hour=7, minute=30, timezone="Asia/Shanghai"),
        id="daily_news_push",
        name="每日新闻推送"
    )
    
    logger.info("⏰ 定时任务已添加：每天北京时间 07:30")
    logger.info("📡 等待执行中...")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ 机器人已停止")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 单次执行模式
        job_news_push()
    else:
        # 定时执行模式
        main()

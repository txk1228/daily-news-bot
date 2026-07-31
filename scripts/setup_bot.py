"""
一键配置：飞书凭证 + 主题 + 推送时间

用法:
  python scripts/setup_bot.py
  python scripts/setup_bot.py --apply-git   # 额外 commit/push 工作流并触发一次 Actions
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "daily_news.yml"

DEFAULT_TOPICS = "AI大模型,具身智能,每日财经热点"
DEFAULT_TIME = "07:30"
MIN_TOPICS = 1
MAX_TOPICS = 5
DEFAULT_REPO = "txk1228/daily-news-bot"


def _mask(value: str, keep: int = 6) -> str:
    if not value:
        return "(空)"
    if len(value) <= keep * 2:
        return value[:2] + "***" + value[-2:]
    return value[:keep] + "..." + value[-keep:]


def _read_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return data
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw[3:].decode("utf-8")
    else:
        text = raw.decode("utf-8")
    for line in text.splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _write_env_file(
    path: Path,
    *,
    webhook: str,
    secret: str,
    topics: str,
    hour: int,
    minute: int,
) -> None:
    content = f"""# ========================================
# 由 scripts/setup_bot.py 生成（勿提交到 Git）
# ========================================

# 飞书群自定义机器人 Webhook
FEISHU_WEBHOOK_URL={webhook}

# 飞书签名校验密钥
FEISHU_SECRET={secret}

# 推送主题（1–5 个，英文逗号分隔）
TOPICS={topics}

# 本地 --schedule / 文档参考用的北京时间
PUSH_HOUR={hour}
PUSH_MINUTE={minute}
"""
    path.write_text(content, encoding="utf-8", newline="\n")


def beijing_to_utc_cron(hour: int, minute: int) -> str:
    """北京时间 HH:MM -> GitHub Actions UTC cron（UTC = CST - 8h）。"""
    utc_hour = (hour - 8) % 24
    return f"{minute} {utc_hour} * * *"


def parse_topics_csv(raw: str) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        topic = part.strip()
        if not topic:
            continue
        key = topic.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(topic)
    if not (MIN_TOPICS <= len(topics) <= MAX_TOPICS):
        raise ValueError(
            f"主题数量须为 {MIN_TOPICS}–{MAX_TOPICS} 个，当前 {len(topics)} 个"
        )
    return topics


def parse_hhmm(raw: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", raw.strip())
    if not m:
        raise ValueError("时间格式须为 HH:MM，例如 07:30")
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("时间超出范围：小时 0–23，分钟 0–59")
    return hour, minute


def validate_webhook(url: str) -> str:
    url = url.strip().lstrip("\ufeff")
    if not url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        raise ValueError(
            "Webhook 须以 https://open.feishu.cn/open-apis/bot/v2/hook/ 开头"
        )
    if "your-webhook-id" in url:
        raise ValueError("请填写真实 Webhook，不要使用占位符")
    return url


def prompt(msg: str, default: str = "") -> str:
    if default:
        hint = f" [{default}]"
    else:
        hint = ""
    try:
        value = input(f"{msg}{hint}: ").strip()
    except EOFError:
        value = ""
    return value if value else default


def write_workflow(topics_csv: str, hour: int, minute: int) -> None:
    cron = beijing_to_utc_cron(hour, minute)
    # YAML 中 topics 含中文/逗号，用双引号包裹
    topics_arg = topics_csv.replace('"', '\\"')
    content = f"""name: Daily News Push

on:
  schedule:
    # 每天北京时间 {hour:02d}:{minute:02d} 执行（UTC cron: {cron}）
    - cron: '{cron}'
  workflow_dispatch:  # 允许手动触发

jobs:
  push-news:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run news push
        env:
          FEISHU_WEBHOOK_URL: ${{{{ secrets.FEISHU_WEBHOOK_URL }}}}
          FEISHU_SECRET: ${{{{ secrets.FEISHU_SECRET }}}}
          TOPICS: "{topics_arg}"
        run: |
          python scripts/news_bot.py --once --topics "{topics_arg}"
"""
    WORKFLOW_PATH.parent.mkdir(parents=True, exist_ok=True)
    WORKFLOW_PATH.write_text(content, encoding="utf-8", newline="\n")


def find_gh() -> str | None:
    return shutil.which("gh")


def gh_logged_in(gh: str) -> bool:
    try:
        r = subprocess.run(
            [gh, "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


def detect_repo(gh: str) -> str:
    try:
        r = subprocess.run(
            [gh, "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except OSError:
        pass
    return DEFAULT_REPO


def set_gh_secrets(gh: str, repo: str, webhook: str, secret: str) -> bool:
    ok = True
    for name, value in (
        ("FEISHU_WEBHOOK_URL", webhook),
        ("FEISHU_SECRET", secret),
    ):
        r = subprocess.run(
            [gh, "secret", "set", name, "-R", repo, "--body", value],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            print(f"  ❌ 写入 Secret {name} 失败: {r.stderr.strip() or r.stdout}")
            ok = False
        else:
            print(f"  ✅ GitHub Secret 已更新: {name}")
    return ok


def apply_git(gh: str | None, repo: str) -> None:
    subprocess.run(["git", "add", str(WORKFLOW_PATH.relative_to(ROOT))], cwd=ROOT, check=False)
    status = subprocess.run(
        ["git", "status", "--porcelain", str(WORKFLOW_PATH.relative_to(ROOT))],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if not status.stdout.strip():
        print("工作流文件无新的 git 变更，跳过 commit。")
    else:
        msg = "chore: 同步一键配置的主题与 Actions 定时"
        r = subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            print(f"commit 失败: {r.stderr or r.stdout}")
            return
        print("✅ 已 commit 工作流变更")
        push = subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if push.returncode != 0:
            print(f"push 失败: {push.stderr or push.stdout}")
            return
        print("✅ 已 push 到远程")

    if not gh:
        print("未找到 gh，跳过触发 Actions。")
        return
    run = subprocess.run(
        [gh, "workflow", "run", "Daily News Push", "-R", repo],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode == 0:
        print(f"✅ 已触发 Actions: https://github.com/{repo}/actions")
    else:
        print(f"触发 Actions 失败: {run.stderr or run.stdout}")


def run_interactive(apply_git_flag: bool) -> int:
    print("=" * 50)
    print("每日新闻机器人 · 一键配置")
    print("=" * 50)
    print("将写入 .env、更新 GitHub Actions 工作流；可选同步 Secrets。\n")

    existing = _read_env_file(ENV_PATH)
    old_webhook = existing.get("FEISHU_WEBHOOK_URL", "")
    old_secret = existing.get("FEISHU_SECRET", "")
    old_topics = existing.get("TOPICS", DEFAULT_TOPICS)
    old_hour = existing.get("PUSH_HOUR", "7")
    old_minute = existing.get("PUSH_MINUTE", "30")
    try:
        old_time = f"{int(old_hour):02d}:{int(old_minute):02d}"
    except ValueError:
        old_time = DEFAULT_TIME

    # Webhook
    while True:
        default_wh = old_webhook if old_webhook and "your-webhook-id" not in old_webhook else ""
        shown = _mask(default_wh) if default_wh else ""
        label = "飞书 Webhook URL"
        if shown:
            label += f"（回车沿用 {_mask(default_wh)}）"
        raw = prompt(label, default_wh)
        try:
            webhook = validate_webhook(raw)
            break
        except ValueError as e:
            print(f"  ❌ {e}")

    # Secret
    while True:
        default_sec = (
            old_secret
            if old_secret and old_secret != "your_feishu_signing_secret"
            else ""
        )
        label = "飞书签名密钥 Secret"
        if default_sec:
            label += f"（回车沿用 {_mask(default_sec)}）"
        raw = prompt(label, default_sec)
        raw = raw.strip().lstrip("\ufeff")
        if not raw or raw == "your_feishu_signing_secret":
            print("  ❌ 请填写真实签名密钥")
            continue
        secret = raw
        break

    # Topics
    while True:
        raw = prompt(
            f"关心的主题（{MIN_TOPICS}–{MAX_TOPICS} 个，英文逗号分隔）",
            old_topics or DEFAULT_TOPICS,
        )
        try:
            topics_list = parse_topics_csv(raw)
            topics_csv = ",".join(topics_list)
            break
        except ValueError as e:
            print(f"  ❌ {e}")

    # Time
    while True:
        raw = prompt("每天推送时间（北京时间 HH:MM）", old_time or DEFAULT_TIME)
        try:
            hour, minute = parse_hhmm(raw)
            break
        except ValueError as e:
            print(f"  ❌ {e}")

    print("\n—— 写入本地配置 ——")
    _write_env_file(
        ENV_PATH,
        webhook=webhook,
        secret=secret,
        topics=topics_csv,
        hour=hour,
        minute=minute,
    )
    print(f"  ✅ 已写入 {ENV_PATH.name}")

    write_workflow(topics_csv, hour, minute)
    cron = beijing_to_utc_cron(hour, minute)
    print(f"  ✅ 已更新 {WORKFLOW_PATH.relative_to(ROOT).as_posix()}")
    print(f"     北京时间 {hour:02d}:{minute:02d} → cron '{cron}'")
    print(f"     主题: {topics_csv}")

    print("\n—— GitHub Secrets ——")
    gh = find_gh()
    repo = detect_repo(gh) if gh else DEFAULT_REPO
    if gh and gh_logged_in(gh):
        set_gh_secrets(gh, repo, webhook, secret)
    elif gh:
        print("  ⚠️ 已安装 gh 但未登录，请先执行: gh auth login")
        print("     然后重新运行本脚本，或手动到仓库 Settings → Secrets 添加。")
    else:
        print("  ⚠️ 未找到 gh CLI。请到 GitHub 仓库 Settings → Secrets 手动添加：")
        print("     FEISHU_WEBHOOK_URL / FEISHU_SECRET")

    print("\n—— 完成 ——")
    print("本地试推:")
    print("  python scripts/news_bot.py --once")
    print("本地定时（按你配置的时间，需保持进程运行）:")
    print("  python scripts/news_bot.py --schedule")
    print("云端: push 工作流后，Actions 会按新时间定时；也可网页 Run workflow。")

    if apply_git_flag:
        print("\n—— --apply-git：提交并触发 ——")
        apply_git(gh if gh and gh_logged_in(gh) else None, repo)
    else:
        print("\n同步工作流到 GitHub（复制执行）:")
        print("  git add .github/workflows/daily_news.yml")
        print('  git commit -m "chore: 同步一键配置的主题与 Actions 定时"')
        print("  git push origin HEAD")
        print("或一次做完（含触发试推）:")
        print("  python scripts/setup_bot.py --apply-git")

    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="一键配置飞书推送主题与定时")
    p.add_argument(
        "--apply-git",
        action="store_true",
        help="commit/push 工作流变更，并尝试触发一次 Daily News Push",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        code = run_interactive(args.apply_git)
    except KeyboardInterrupt:
        print("\n已取消。")
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()

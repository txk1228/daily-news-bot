# GitHub Actions 部署指南（免费永久运行）

用 GitHub Actions 每天定时拉取公开 RSS 新闻，并推送到飞书群。无需 Coze API Key。

## 方案优势

| 对比 | Render 免费版 | GitHub Actions |
|------|--------------|----------------|
| 费用 | 有限制 | 完全免费 |
| 时长限制 | 15分钟 | 3600分钟/次 |
| 休眠问题 | 会休眠 | 不会 |
| 推荐 | 备选 | 推荐 |

---

## 部署步骤

### 第一步：创建 GitHub 仓库

1. 访问 https://github.com
2. 新建仓库，例如 `daily-news-bot`（建议 Private）
3. 将本项目推送到该仓库

### 第二步：设置密钥（Secrets）

进入仓库 → **Settings** → **Secrets and variables** → **Actions**，添加：

| Name | Value |
|------|--------|
| `FEISHU_WEBHOOK_URL` | `https://open.feishu.cn/open-apis/bot/v2/hook/xxx` |
| `FEISHU_SECRET` | 飞书机器人签名密钥 |

不需要配置 Coze 相关密钥。新闻来自公开 Google News RSS。

### 第三步：自定义主题（可选）

编辑 [`.github/workflows/daily_news.yml`](.github/workflows/daily_news.yml) 中的运行命令，通过 `--topics` 指定 1–5 个主题（英文逗号分隔）。不传则默认 `AI大模型,自动驾驶`。

```yaml
run: |
  python scripts/news_bot.py --once --topics "AI大模型,自动驾驶,芯片"
```

### 第四步：验证部署

1. 打开仓库 **Actions** → **Daily News Push**
2. **Run workflow** → 手动跑一次
3. 查看日志，并确认飞书群收到消息

---

## 完成后

- 每天北京时间 **08:30** 自动推送
- 电脑关机也不影响

## 修改推送时间

编辑 `.github/workflows/daily_news.yml`：

```yaml
on:
  schedule:
    # 北京时间 08:30 = UTC 00:30
    - cron: '30 0 * * *'
```

| 北京时间 | UTC |
|---------|-----|
| 07:30 | `30 23 * * *`（前一天） |
| 08:00 | `0 0 * * *` |
| 08:30 | `30 0 * * *` |
| 09:00 | `0 1 * * *` |

## 本地测试

```bash
cp .env.example .env   # 填入飞书配置后
pip install -r requirements.txt
# 需先 export / 设置环境变量，或在 shell 中加载 .env
python scripts/news_bot.py --once --topics "AI大模型,自动驾驶"
```

## 项目文件

```
daily-news-bot/
├── .github/workflows/daily_news.yml
├── scripts/news_bot.py
├── requirements.txt
├── .env.example
└── README_GITHUB_ACTIONS.md
```

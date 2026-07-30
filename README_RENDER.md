# Render 免费部署指南 - 每日科技新闻推送机器人

通过公开 RSS 按自定义主题拉取资讯，定时推送到飞书群。无需 Coze API Key。

## 部署步骤

### 第一步：上传代码到 GitHub

创建仓库并推送本项目代码（可用 Private 仓库）。

### 第二步：在 Render 上部署

1. 注册/登录 [Render](https://render.com)，用 GitHub 账号授权
2. **New** → **Cron Job**
3. 配置示例：
   - **Name**: `daily-news-bot`
   - **Region**: Singapore
   - **Schedule**: `30 23 * * *`（UTC = 北京时间 07:30）
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python scripts/news_bot.py --once --topics "AI大模型,自动驾驶"`
4. 连接 GitHub 仓库，Branch: `main`
5. 在 **Environment** 添加：

| 变量名 | 必须 | 说明 |
|--------|------|------|
| `FEISHU_WEBHOOK_URL` | 是 | 飞书群机器人 Webhook |
| `FEISHU_SECRET` | 是 | 签名校验密钥 |
| `PYTHONUNBUFFERED` | 否 | 建议设为 `1`，日志实时输出 |

也可用仓库根目录的 `render.yaml` Blueprint 创建（记得把 `owner` 改成你的邮箱，并在控制台填写飞书密钥）。

### 自定义主题

在 Start Command 中通过 `--topics` 指定 1–5 个主题（英文逗号分隔）。不传则默认 `AI大模型,自动驾驶`。

```text
python scripts/news_bot.py --once --topics "AI大模型,自动驾驶,芯片"
```

### 第三步：验证

在 Render Dashboard 点 **Run Now**，看日志是否成功，并检查飞书群。

---

## 说明

### 免费版限制

- 每月约 500 次 Cron 执行（每天 1 次足够）
- 冷启动可能有短暂延迟

### 新闻来源

脚本使用 Google News RSS（中文），不依赖 Coze / 第三方搜索 API Key。

### 推送时间

| 表达式 | 说明 |
|--------|------|
| `30 23 * * *` | UTC 23:30 = **北京时间 07:30** |

修改 `render.yaml` 的 `schedule` 即可（须用 UTC）。

### 常见问题

**消息发送失败？**  
检查 Webhook 是否有效、是否开启了签名校验且 `FEISHU_SECRET` 正确。

**搜索失败 / 无新闻？**  
确认运行环境能访问 `news.google.com`；可本地先跑 `python scripts/news_bot.py --once` 看日志。

**如何手动触发？**  
Render Dashboard → Cron Job → **Run Now**。

---

## 本地测试

```bash
cp .env.example .env
# 填写 FEISHU_WEBHOOK_URL / FEISHU_SECRET
pip install -r requirements.txt
set FEISHU_WEBHOOK_URL=...   # Windows PowerShell 用 $env:...
set FEISHU_SECRET=...
python scripts/news_bot.py --once --topics "AI大模型,自动驾驶"
```

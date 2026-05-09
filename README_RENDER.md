# 🚀 Render 免费部署指南 - 每日科技新闻推送机器人

## 📋 部署步骤

### 第一步：上传代码到 GitHub

1. **创建 GitHub 仓库**
   - 访问 https://github.com/new
   - 仓库名称：`daily-news-bot`
   - 选择 Private（私有）
   - 不要初始化 README

2. **上传代码到仓库**
   ```bash
   cd /workspace/projects
   
   # 初始化 git
   git init
   git add .
   git commit -m "feat: 每日科技新闻推送机器人"
   
   # 关联远程仓库（替换为你的仓库地址）
   git remote add origin https://github.com/你的用户名/daily-news-bot.git
   
   # 推送
   git branch -M main
   git push -u origin main
   ```

### 第二步：在 Render 上部署

1. **注册/登录 Render**
   - 访问 https://render.com
   - 使用 GitHub 账号登录

2. **创建 Cron Job**
   - 点击 **New** → **Cron Job**
   
3. **配置 Cron Job**
   - **Name**: `daily-news-bot`
   - **Region**: Singapore
   - **Schedule**: `30 23 * * *`（UTC 时间，北京时间 07:30）
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python scripts/news_bot.py`

4. **连接 GitHub 仓库**
   - 选择你刚创建的仓库
   - Branch: `main`

5. **设置环境变量**（关键步骤！）

   点击 **Environment** 添加以下环境变量：

   | 变量名 | 值 |
   |--------|-----|
   | `FEISHU_WEBHOOK_URL` | `your_feishu_webhook_url` |
   | `PYTHONUNBUFFERED` | `1` |
   | `COZE_WORKLOAD_IDENTITY_API_KEY` | （从平台获取的 API Key） |

6. **点击 Create Cron Job**

### 第三步：验证部署

1. **手动触发测试**
   - 在 Render Dashboard 点击 **Run Now** 按钮
   - 查看日志确认是否发送成功

2. **检查飞书群**
   - 确认收到推送消息

---

## ⚠️ 重要说明

### 免费版限制
- **每月 500 次执行**（我们的 cron 每天 1 次，完全够用）
- **冷启动延迟**（免费版可能延迟几分钟）
- **睡眠策略**：免费版 15 分钟无活动会休眠，但 cron 会保持唤醒

### 环境变量说明

| 变量名 | 必须 | 说明 |
|--------|------|------|
| `FEISHU_WEBHOOK_URL` | ✅ | 飞书群机器人 Webhook 地址 |
| `COZE_WORKLOAD_IDENTITY_API_KEY` | ✅ | Coze 平台 API Key |
| `PYTHONUNBUFFERED` | 可选 | 让日志实时输出 |

### 获取 COZE_WORKLOAD_IDENTITY_API_KEY
1. 登录 Coze 平台
2. 进入项目设置 → API Key
3. 复制并添加到 Render 环境变量

---

## 🕐 推送时间

| 表达式 | 说明 |
|--------|------|
| `30 23 * * *` | 每天 UTC 23:30 = **北京时间 07:30** |

如需修改时间，编辑 `render.yaml` 中的 schedule 值（必须是 UTC 时间）。

---

## 📁 项目文件结构

```
daily-news-bot/
├── scripts/
│   └── news_bot.py          # 主脚本（定时推送逻辑）
├── requirements.txt          # Python 依赖
├── render.yaml              # Render 部署配置
└── README.md                # 本文档
```

---

## 🔧 常见问题

### Q: 消息发送失败？
A: 检查飞书 Webhook 是否有效，重新创建自定义机器人获取新的 Webhook URL。

### Q: 搜索失败？
A: 确认 `COZE_WORKLOAD_IDENTITY_API_KEY` 环境变量已正确设置。

### Q: 如何手动触发推送？
A: 在 Render Dashboard 点击 Cron Job 的 **Run Now** 按钮。

---

## 🎉 部署完成！

从此你的新闻推送机器人将：
- ☁️ 永久运行在云端
- ⏰ 每天早上 7:30 自动推送
- 📱 发送到你的飞书群
- 💻 电脑关机也没关系！

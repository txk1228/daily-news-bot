# 🚀 GitHub Actions 部署指南（免费永久运行）

## 方案优势

| 对比 | Render 免费版 | GitHub Actions |
|------|--------------|----------------|
| 费用 | 有限制 | ✅ 完全免费 |
| 时长限制 | 15分钟 | ✅ 3600分钟/次 |
| 休眠问题 | 会休眠 | ✅ 不会 |
| 推荐 | ❌ | ✅ 强烈推荐 |

---

## 📋 部署步骤（10分钟完成）

### 第一步：创建 GitHub 仓库

1. 访问 https://github.com
2. 点击右上角 **+** → **New repository**
3. 填写：
   - Repository name: `daily-news-bot`
   - 选择 **Private**（更安全）
   - 点击 **Create repository**

### 第二步：上传代码到 GitHub

在终端执行（替换 `你的用户名`）：

```bash
cd /workspace/projects

# 初始化（如果没有初始化过）
git init
git add .
git commit -m "feat: 每日新闻推送机器人"

# 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/daily-news-bot.git

# 推送代码
git branch -M main
git push -u origin main
```

### 第三步：设置密钥（Secrets）

1. 进入你的 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**，添加两个：

**Secret 1:**
- Name: `FEISHU_WEBHOOK_URL`
- Value: `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`

**Secret 2:**
- Name: `FEISHU_SECRET`
- Value: `your_feishu_signing_secret`

### 第四步：验证部署

1. 进入你的仓库
2. 点击 **Actions** 标签
3. 点击左侧 **Daily News Push**
4. 点击 **Run workflow** → **Run workflow**
5. 查看运行状态

---

## ✅ 完成！

- **每天北京时间 08:30** 自动推送
- **完全免费**，无需电脑开机
- **永久运行**，不受任何限制

---

## 🔧 其他配置

### 修改推送时间

编辑 `.github/workflows/daily_news.yml`：

```yaml
on:
  schedule:
    # 北京时间 08:30 = UTC 00:30
    - cron: '30 0 * * *'
```

常用时间对照：
| 北京时间 | UTC |
|---------|-----|
| 07:30 | 23:30 |
| 08:00 | 00:00 |
| 08:30 | 00:30 |
| 09:00 | 01:00 |

### 手动触发

进入仓库 → Actions → Daily News Push → Run workflow

---

## 📁 项目文件说明

```
daily-news-bot/
├── .github/
│   └── workflows/
│       └── daily_news.yml    # GitHub Actions 配置
├── scripts/
│   └── news_bot.py           # 主推送脚本
├── requirements.txt          # 依赖包
└── README.md                 # 项目说明
```

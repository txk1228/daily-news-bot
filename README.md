# 每日科技新闻推送机器人

按自定义主题拉取公开 RSS 资讯，签名后推送到**飞书群**。无需 Coze / OpenAI API Key。

**推荐用法**：用 [GitHub Actions](https://github.com/txk1228/daily-news-bot/actions) 云端定时 / 手动推送——**电脑关机也没关系**。本地 `--schedule` 仅作备选。

## 效果预览

飞书消息按主题分块，每块内 **1）2）3）** 分点列出，并带来源标签与链接：

```text
🔔 小可每日资讯 | AI大模型 & 具身智能 & 每日财经热点
📅 2026 年 07 月 31 日

📌 AI大模型
1）……标题…… [来源] 🔗 https://...
2）……标题…… [来源] 🔗 https://...
3）……标题…… [来源] 🔗 https://...

📌 具身智能
1）……
2）……
3）……

📌 每日财经热点
1）……标题…… [虎嗅] 🔗 https://www.huxiu.com/...
2）……
3）……

✨ 每日积累，稳步精进～
```

实拍效果图：

![飞书推送效果](assets/feishu-demo.png)

### 默认主题

| 序号 | 主题 | 主要来源 |
|------|------|----------|
| 1 | `AI大模型` | Google News（定制检索）→ 国内科技 RSS 回退 |
| 2 | `具身智能` | Google News（人形机器人等）→ 国内科技 RSS 回退 |
| 3 | `每日财经热点` | **虎嗅 RSS 优先**，辅以 36氪；不足再用华尔街见闻 / 财联社等检索 |

也可用 `--topics` 临时换成别的主题（1–5 个，英文逗号分隔）。

---

## 功能概览

| 能力 | 说明 |
|------|------|
| 主题推送 | 默认三维主题；支持 1–5 个自定义主题 |
| 消息排版 | 各板块下 **1）2）3）** 分点，带 `[来源]` 与链接 |
| 新闻源 | 主题专业源优先（财经→虎嗅）→ 定制 Google 检索 → IT之家 / 36氪 / Solidot |
| 飞书安全 | 自定义机器人 **Webhook + 签名校验**（可配合自定义关键词） |
| **云端（推荐）** | GitHub Actions：每天约北京时间 **07:30** 自动推；也可随时点 **Run workflow** |
| 本地 | `--once` 推一次；`--schedule` 需进程一直挂着（关机/休眠会停） |

---

## 1. 配置飞书机器人（必做）

### 1.1 添加自定义机器人

1. 打开目标飞书群 → 右上角 `...` → **群机器人** → **添加机器人**
2. 选择 **自定义机器人**，起名后添加
3. 复制 **Webhook 地址**（形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx`）

> 不要把 Webhook 发到公开仓库或群聊外链，泄露后可能被滥用发垃圾消息。

### 1.2 安全设置（本项目需要）

在机器人详情 → **安全设置** 中建议同时开启：

1. **签名校验**（必开）  
   - 复制生成的 **密钥（secret）**
2. **自定义关键词**（建议开启）  
   - 至少包含：`小可每日资讯`（脚本消息标题里会带上该词）  
   - 可选再加：`自动驾驶推送`

关键词在 **安全设置 → 自定义关键词** 中填写，每行一个。

常见报错对照：

| 飞书返回 | 含义 | 处理 |
|----------|------|------|
| `19001` access token invalid | Webhook 地址错误或仍是占位符 | 检查 Webhook URL |
| `19021` sign match fail | 签名密钥不对 / 未开签名 | 核对 Secret，确认已开启签名校验 |
| `19024` Key Words Not Found | 开了关键词但正文不含任一关键词 | 关键词加上 `小可每日资讯`，或关闭关键词校验 |

### 1.3 本地 `.env`（仅本地运行需要）

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

```env
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的真实ID
FEISHU_SECRET=你的真实签名密钥
```

主题**不写在** `.env` 里。云端请把同样两项配到 GitHub Secrets（见下一节）。

---

## 2. GitHub Actions 云端推送（推荐，不必开机）

仓库已包含工作流 [`.github/workflows/daily_news.yml`](.github/workflows/daily_news.yml)。配置好 Secrets 后：

- **自动**：每天约北京时间 **07:30** 推送（GitHub 定时偶有延迟，属正常）
- **手动**：打开 Actions → **Run workflow**，随时补推一次——**不需要电脑开机或挂着终端**

### 2.1 配置 Secrets（只需一次）

打开仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加：

| Name | Value |
|------|--------|
| `FEISHU_WEBHOOK_URL` | 飞书 Webhook 完整地址 |
| `FEISHU_SECRET` | 飞书签名校验密钥 |

本仓库示例：[txk1228/daily-news-bot](https://github.com/txk1228/daily-news-bot)（Settings 仅仓库管理员可见）。

### 2.2 手动推送（Run workflow）

1. 打开 [Actions](https://github.com/txk1228/daily-news-bot/actions)
2. 左侧点 **Daily News Push**
3. 右侧 **Run workflow** → 选 `main` → 再点绿色 **Run workflow**
4. 等约 1 分钟，点进最新 run 看日志；飞书群应收到消息

命令行等价操作（需已登录 [`gh`](https://cli.github.com/)）：

```bash
gh workflow run "Daily News Push" -R txk1228/daily-news-bot
gh run list -R txk1228/daily-news-bot --workflow="Daily News Push" --limit 3
```

### 2.3 自动定时

工作流使用：

```yaml
on:
  schedule:
    # 北京时间 07:30 = UTC 前一天 23:30
    - cron: '30 23 * * *'
  workflow_dispatch:  # 允许网页 / gh 手动触发
```

当前默认主题（可在 `daily_news.yml` 里改）：

```bash
python scripts/news_bot.py --once --topics "AI大模型,具身智能,每日财经热点"
```

更细的说明见 [README_GITHUB_ACTIONS.md](README_GITHUB_ACTIONS.md)。

### 2.4 和本地定时的区别

| 方式 | 电脑要开着吗 | 适用场景 |
|------|--------------|----------|
| **GitHub Actions（推荐）** | **否** | 每天自动 + 随时点 Run workflow |
| 本地 `python scripts/news_bot.py --schedule` | **是**（休眠/关机即停） | 临时调试 |
| 本地 `--once` | 运行那一下要开着 | 本机立刻测通飞书 |

---

## 3. 本地安装与运行（可选）

### 3.1 安装依赖

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\pip.exe install -r requirements.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 推送一次

```bash
# Windows
.\.venv\Scripts\python.exe scripts\news_bot.py --once

# Linux / macOS
python scripts/news_bot.py --once
```

成功日志示例：

```text
✅ 推送成功！
飞书响应: {'code': 0, 'msg': 'success', ...}
```

### 3.3 自定义主题

主题数量 **1–5**，英文逗号分隔；不传则默认 `AI大模型,具身智能,每日财经热点`。

```bash
python scripts/news_bot.py --once --topics "AI大模型,具身智能,每日财经热点"
python scripts/news_bot.py --once --topics "量子计算,机器人"
```

默认主题带同义词过滤（如「大模型」「人形机器人」「融资/财报」等）；财经板块另走虎嗅等专业源。

### 3.4 本地长驻定时（不推荐作为主力）

```bash
python scripts/news_bot.py --schedule
```

进程必须一直运行。日常请用 **第 2 节 GitHub Actions**。

---

## 4. 新闻从哪来

拉取顺序（见 `scripts/news_bot.py`）：

```text
1. 主题专业源（若配置）
   · 每日财经热点 → https://rss.huxiu.com/ 、36氪
2. Google News（主题定制检索词）
   · 财经：虎嗅 / 华尔街见闻 / 财联社 / 第一财经 / 界面新闻 …
   · 具身智能：人形机器人 / 优必选 / 智元 / 宇树 …
   · AI大模型：大模型 / DeepSeek / OpenAI / Kimi …
3. 通用回退：IT之家 / 36氪 / Solidot + 同义词过滤
```

每主题最多 **3** 条；飞书正文格式为：

```text
📌 主题名
1）标题 [来源] 🔗 链接
2）标题 [来源] 🔗 链接
3）标题 [来源] 🔗 链接
```

会过滤「个人中心」、部分地方站等杂讯标题。无需任何新闻 API Key。

---

## 5. 命令速查

| 命令 | 作用 |
|------|------|
| `python scripts/news_bot.py --once` | 本地推送一次后退出 |
| `python scripts/news_bot.py --schedule` | 本地每天 07:30（需进程常驻） |
| `--topics "主题1,主题2"` | 指定 1–5 个主题 |
| Actions → **Run workflow** | 云端立刻推一次（不必开机） |

环境变量 / Secrets：

| 变量 | 是否必填 | 说明 |
|------|----------|------|
| `FEISHU_WEBHOOK_URL` | 是 | 飞书自定义机器人 Webhook |
| `FEISHU_SECRET` | 是 | 签名校验密钥 |

---

## 6. 其他云端方案

- GitHub Actions（推荐）：见上文与 [README_GITHUB_ACTIONS.md](README_GITHUB_ACTIONS.md)
- Render：见 [README_RENDER.md](README_RENDER.md)

---

## 7. Coze Agent / HTTP（可选）

本仓库另含 Coze 相关运行脚本；**日常飞书推送不依赖它们**。

```bash
bash scripts/local_run.sh -m flow
bash scripts/http_run.sh -m http -p 5000
```

---

## 常见问题

**Q: 电脑关机了还会推吗？**  
会——只要用的是 GitHub Actions（已配 Secrets）。本地 `--schedule` 关机后不会推；可到 Actions 点 **Run workflow** 补推。

**Q: 定时到点了还没收到？**  
GitHub 的 `schedule` 有时会延迟。可打开 Actions 看是否已跑；没有就点 **Run workflow**。

**Q: 财经为什么以前会出现地方杂讯？**  
泛搜「每日财经热点」易命中地方站。现已改为 **虎嗅 RSS 优先**，并用专业媒体检索词补充。

**Q: 提示「未获取到任何新闻，任务终止」？**  
专业源与 Google 都暂时不可达，且国内回退未命中。稍后再跑，或换更宽的 `--topics`。

**Q: 飞书报错？**  
对照第 1.2 节错误表；并确认 GitHub Secrets 无 BOM、无多余空格/引号。

# 每日科技新闻推送机器人

按自定义主题拉取公开 RSS 资讯，签名后推送到**飞书群**。无需 Coze / OpenAI API Key，本地一次推送或每天定时均可。

## 效果预览

推送到飞书后大致如下（标题含关键词「小可每日资讯」，按主题分块展示标题 + 链接）：
![Uploading image.png…]()

飞书推送效果

默认主题为 `AI大模型`、`自动驾驶`；也可用 `--topics` 换成例如 `AI大模型,人形机器人,芯片`。

---

## 功能概览


| 能力   | 说明                                                       |
| ---- | -------------------------------------------------------- |
| 主题推送 | 支持 1–5 个主题，英文逗号分隔                                        |
| 新闻源  | 优先 Google News RSS；不可达时回退 IT之家 / 36氪 / Solidot，并按主题同义词过滤 |
| 飞书安全 | 使用自定义机器人 **Webhook + 签名校验**（并可配合自定义关键词）                  |
| 运行方式 | `--once` 推一次；`--schedule` 每天北京时间 **07:30** 自动推           |


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
  - 复制生成的 **密钥（secret）**，填入下面的 `.env`
2. **自定义关键词**（建议开启）
  - 至少包含：`小可每日资讯`（脚本消息标题里会带上该词）  
  - 可选再加：`自动驾驶推送`

关键词在机器人详情 → **安全设置 → 自定义关键词** 中填写，每行一个。

常见报错对照：


| 飞书返回                         | 含义                 | 处理                                |
| ---------------------------- | ------------------ | --------------------------------- |
| `19001` access token invalid | Webhook 地址错误或仍是占位符 | 检查 `.env` 中的 `FEISHU_WEBHOOK_URL` |
| `19021` sign match fail      | 签名密钥不对 / 未开签名      | 核对 `FEISHU_SECRET`，确认已开启签名校验      |
| `19024` Key Words Not Found  | 开了关键词但正文不含任一关键词    | 关键词加上 `小可每日资讯`，或关闭关键词校验           |




### 1.3 填写 `.env`

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
cp .env.example .env
```

编辑项目根目录 `.env`：

```env
# 飞书群自定义机器人 Webhook（整段粘贴，不要加引号）
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/你的真实ID

# 飞书签名校验密钥（与机器人安全设置中一致）
FEISHU_SECRET=你的真实签名密钥
```

主题**不写在** `.env` 里，用命令行 `--topics` 指定（见下文）。

---



## 2. 安装与运行



### 2.1 创建虚拟环境并安装依赖

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\pip.exe install -r requirements.txt

# Linux / macOS
source .venv/bin/activate
pip install -r requirements.txt
```



### 2.2 推送一次（推荐先测通）

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



### 2.3 自定义主题

主题数量 **1–5**，英文逗号分隔；不传则默认 `AI大模型,自动驾驶`。

```bash
python scripts/news_bot.py --once --topics "AI大模型,自动驾驶,芯片"
python scripts/news_bot.py --once --topics "量子计算,机器人"
python scripts/news_bot.py --once --topics "AI大模型,人形机器人,芯片"
```

对默认主题 `AI大模型` / `自动驾驶`，国内回退源会使用内置同义词（如「大模型」「智驾」「智能网联」等）提高命中率。

### 2.4 长驻定时（每天 07:30 北京时间）

```bash
python scripts/news_bot.py --schedule
python scripts/news_bot.py --schedule --topics "AI大模型,自动驾驶"
```

进程需保持运行（电脑休眠/关机后不会推送）。需要无人值守更推荐下面的云端方案。

---



## 3. 新闻从哪来

```text
优先：Google News RSS（按主题检索）
   ↓ 失败（如国内 SSL / 网络问题）
回退：IT之家 / 36氪 / Solidot
   ↓
按主题关键词（及同义词）过滤，每主题最多 3 条
```

无需任何新闻 API Key。

---



## 4. 命令速查


| 命令                                      | 作用               |
| --------------------------------------- | ---------------- |
| `python scripts/news_bot.py --once`     | 推送一次后退出（默认行为）    |
| `python scripts/news_bot.py --schedule` | 每天 07:30（北京时间）推送 |
| `--topics "主题1,主题2"`                    | 指定 1–5 个主题       |


环境变量（见 `.env.example`）：


| 变量                   | 是否必填 | 说明               |
| -------------------- | ---- | ---------------- |
| `FEISHU_WEBHOOK_URL` | 是    | 飞书自定义机器人 Webhook |
| `FEISHU_SECRET`      | 是    | 签名校验密钥           |


---



## 5. 云端部署（可选）

适合不想本机长开终端的场景：

- **GitHub Actions（推荐）**：见 [README_GITHUB_ACTIONS.md](README_GITHUB_ACTIONS.md)
- **Render**：见 [README_RENDER.md](README_RENDER.md)

在 GitHub Secrets / Render 环境变量中配置同样的 `FEISHU_WEBHOOK_URL`、`FEISHU_SECRET` 即可。

---



## 6. Coze Agent / HTTP（可选）

本仓库另含 Coze 相关运行脚本；**日常飞书推送不依赖它们**。

```bash
bash scripts/local_run.sh -m flow
bash scripts/http_run.sh -m http -p 5000
```

---



## 常见问题

**Q: 提示「未获取到任何新闻，任务终止」？**  
Google News 可能暂时不可达，且国内源标题未命中主题词。可换更宽的主题词重试，或稍后再跑；默认两个主题已带同义词，一般能筛出内容。

**Q: 飞书收到测试消息，但** `--once` **仍失败？**  
先看日志是卡在「拉取新闻」还是「飞书响应」。新闻为 0 不会调用飞书；飞书 `code != 0` 再对照上文错误表。

**Q: 定时模式没有推送？**  
确认进程仍在运行，时区任务为北京时间 07:30；也可用 `--once` 随时手动补推。

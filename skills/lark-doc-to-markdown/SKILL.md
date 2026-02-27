---
name: lark-doc-to-markdown
description: 将 Lark/飞书文档转换为 Markdown 格式文档，便于 AI 阅读与后续分析。当用户提供 Lark 文档链接并请求分析、导出或转换时使用；转换后的 Markdown 可作为其他 Skill 或 AI 分析的输入。当用户提到"转 Markdown"、"转飞书文档"、"转 Lark 文档"时，也可触发此 Skill。
---

# Lark 文档转 Markdown（全局 Skill）

本 Skill 安装在 **个人技能目录** `~/.cursor/skills/lark-doc-to-markdown/`，可在任意项目中全局使用。

## 何时使用

- 用户提供一个 **Lark/飞书文档链接** 并希望进行分析、总结或后续操作时
- 需要把飞书文档内容转为可被 AI 直接阅读的 Markdown 时

## 执行步骤

1. **在当前项目目录下执行**（确保当前目录或上级目录有 `.env`，内含 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`）：
   ```bash
   python3 ~/.cursor/skills/lark-doc-to-markdown/scripts/main.py <文档URL> --output output.md
   ```
   - **执行时长**：脚本拉取文档、调用飞书 API 并转换可能**需要较长时间**（文档越大越久）。执行该命令时**必须给予足够长的等待时间**，不得因超时提前终止；若环境有超时限制，应设置为足够大（例如数分钟以上）。
   - 将 `<文档URL>` 替换为用户提供的完整 Lark/飞书文档链接（如 `https://xxx.feishu.cn/wiki/...` 或 `https://xxx.larksuite.com/wiki/...`）
   - 脚本从**当前工作目录**加载 `.env`，输出文件 `output.md` 也写在当前目录；可在任意含 `.env` 的项目目录下执行

2. **根据执行结果处理**：
   - **成功**：告知用户已生成 `output.md`，该文件可作为后续 AI 分析、总结或其他 Skill 的输入
   - **报错**：**立即返回对应提醒并终止处理**，不继续后续步骤；待用户修正错误后，由用户再次发起转换请求后继续。

## 错误与提醒

**原则**：一旦检测到错误信息，必须**返回提醒并终止处理**，让用户先修正错误，修正后再由用户重新执行或请求继续。

| 报错信息 | 对用户的提醒 |
|----------|----------------|
| 输出或异常中出现 `permission denied`（不区分大小写） | **需要把文档分享到有 Lark 机器人（doc_to_markdown）的群里** |
| 输出或异常中出现 `FEISHU_APP_ID and FEISHU_APP_SECRET must be set in .env file` | **需要配置 .env 文件**（在当前项目根目录创建 `.env`，填写 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`） |

执行脚本后，若检测到上述任一报错：**仅返回上表对应提醒并明确告知「已终止处理，请先按提醒修正后再继续」**；可补充配置与权限说明，但不进行后续转换或分析步骤。

## 脚本说明

**注意**：脚本执行（拉取文档 + API 调用 + 转换）可能较慢，调用方**必须设置足够长的超时/等待时间**，避免中途因超时中断。

| 文件 | 说明 |
|------|------|
| `~/.cursor/skills/lark-doc-to-markdown/scripts/main.py` | 入口脚本，从当前目录加载 `.env`，解析 URL、拉取文档并转换为 Markdown（执行可能较久，需足够等待） |
| `scripts/feishu_client.py` | 飞书 API 客户端 |
| `scripts/converter.py` | 文档块转 Markdown 的转换逻辑 |

**依赖**：需在系统或当前环境中安装 `lark-oapi`、`python-dotenv`（如 `pip install lark-oapi python-dotenv`）。每个使用本 Skill 的项目需在**当前项目目录**配置 `.env`（FEISHU_APP_ID、FEISHU_APP_SECRET）。

## 输出与后续使用

- 成功时生成的 Markdown 文件（默认当前目录下的 `output.md`）可直接作为当前对话中 AI 分析、总结、问答的输入，或其他 Skill/工作流的文档输入。
- 在回复用户时，可说明「已从 Lark 文档生成 Markdown，文件路径为 xxx，可直接基于该文件进行后续分析」。

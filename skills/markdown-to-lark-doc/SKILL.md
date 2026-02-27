---
name: markdown-to-lark-doc
description: 将 Markdown 格式文档导入/写入到 Lark/飞书文档中。当用户提供 Markdown 文件路径和 Lark 文档链接并请求导入、写入或同步时使用。
---

# Markdown 转 Lark 文档（全局 Skill）

本 Skill 安装在 **个人技能目录** `~/.cursor/skills/markdown-to-lark-doc/`，可在任意项目中全局使用。

## 何时使用

- 用户提供一个 **Markdown 文件** 和一个 **Lark/飞书文档链接**，并希望将 Markdown 内容写入到该文档时
- 需要将本地的 Markdown 文档内容同步到飞书文档时

## 执行步骤

1. **在当前项目目录下执行**（确保当前目录或上级目录有 `.env`，内含 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`）：
   ```bash
   ~/.cursor/skills/markdown-to-lark-doc/venv/bin/python ~/.cursor/skills/markdown-to-lark-doc/scripts/main.py --import-file <Markdown文件路径> <目标文档URL>
   ```
   - **执行时长**：脚本解析 Markdown 并调用飞书 API 创建文档块可能**需要较长时间**（内容越多越久）。执行该命令时**必须给予足够长的等待时间**，不得因超时提前终止。
   - 将 `<Markdown文件路径>` 替换为用户提供的 Markdown 文件路径。
   - 将 `<目标文档URL>` 替换为用户提供的完整 Lark/飞书文档链接（如 `https://xxx.feishu.cn/wiki/...`）。
   - 脚本从**当前工作目录**加载 `.env`。

2. **根据执行结果处理**：
   - **成功**：告知用户已成功将 Markdown 内容写入到目标 Lark 文档。
   - **报错**：**立即返回对应提醒并终止处理**，不继续后续步骤；待用户修正错误后，由用户再次发起请求后继续。

## 错误与提醒

**原则**：一旦检测到错误信息，必须**返回提醒并终止处理**，让用户先修正错误，修正后再由用户重新执行或请求继续。

| 报错信息 | 对用户的提醒 |
|----------|----------------|
| 输出或异常中出现 `permission denied`（不区分大小写） | **需要把文档分享到有 Lark 机器人（doc_to_markdown）的群里，并确保机器人有编辑权限** |
| 输出或异常中出现 `FEISHU_APP_ID and FEISHU_APP_SECRET must be set in .env file` | **需要配置 .env 文件**（在当前项目根目录创建 `.env`，填写 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`） |
| 输出或异常中出现 `Input file ... not found` | **请检查 Markdown 文件路径是否正确** |

执行脚本后，若检测到上述任一报错：**仅返回上表对应提醒并明确告知「已终止处理，请先按提醒修正后再继续」**。

## 脚本说明

**注意**：脚本执行（解析 + API 调用）可能较慢，调用方**必须设置足够长的超时/等待时间**，避免中途因超时中断。

| 文件 | 说明 |
|------|------|
| `~/.cursor/skills/markdown-to-lark-doc/scripts/main.py` | 入口脚本，从当前目录加载 `.env`，解析 Markdown 并写入 Lark 文档 |
| `scripts/markdown_to_lark.py` | Markdown 解析与转换逻辑 |

**依赖**：需在系统或当前环境中安装 `lark-oapi`、`python-dotenv`。每个使用本 Skill 的项目需在**当前项目目录**配置 `.env`（FEISHU_APP_ID、FEISHU_APP_SECRET）。

# 飞书文档转 Markdown 工具

本工具使用飞书开放平台 API 将飞书（Lark）文档转换为 Markdown 格式，同时也支持将 Markdown 导入回飞书文档。

## 前置条件

1.  **Python 3.8+**
2.  **飞书/Lark 应用**：需要在[飞书开发者后台](https://open.feishu.cn/app)创建应用并获取 `App ID` 和 `App Secret`。
3.  **权限**：确保应用拥有以下权限：
```JSON 
{
  "scopes": {
    "tenant": [
      "docs:doc:readonly",
      "docx:document",
      "docx:document:readonly",
      "docx:document:write_only",
      "drive:drive:readonly",
      "im:resource",
      "wiki:wiki:readonly"
    ],
    "user": []
  }
}
```
如果只需要导出功能，可以不需要 `docx:document:write_only` 和 `docx:document` 权限。

## 安装

1.  克隆本仓库。
2.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

## 配置

1.  复制 `env.example` 到 `.env`：
    ```bash
    cp env.example .env
    ```
2.  编辑 `.env` 并填写你的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`。

## 使用方法

### 导出（飞书 -> Markdown）

使用 Wiki Token 或 URL 运行脚本：

```bash
python scripts/main.py <WIKI_TOKEN_OR_URL>
```

示例：

```bash
python scripts/main.py wikcnAbc123Def456
# 或者
python scripts/main.py https://your-org.feishu.cn/wiki/wikcnAbc123Def456
```

默认输出保存为 `output.md`。你可以通过 `-o` 参数指定输出文件：

```bash
python scripts/main.py <TOKEN> -o my_doc.md
```

### 导入（Markdown -> 飞书）

将 Markdown 文件导入到现有的飞书文档中。

**注意：** 飞书机器人必须拥有目标文档的**编辑**权限。

```bash
python scripts/main.py --import-file <MARKDOWN_FILE> <WIKI_TOKEN_OR_URL>
```

示例：

```bash
python scripts/main.py --import-file input.md https://your-org.feishu.cn/wiki/wikcnAbc123Def456
```

**Mermaid 支持：**
工具支持导入 Mermaid 图表（`mermaid` 代码块）。
*   它会自动将其转换为飞书的“文本绘图”块。
*   **提示：** 如果遇到渲染问题，请先在目标文档中手动创建一个“文本绘图”块。工具会自动从中发现正确的组件 ID。


### 文档授权
参考 [USAGE.md](USAGE.md)

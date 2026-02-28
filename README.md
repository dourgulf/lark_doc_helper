# Lark Doc to Markdown Converter

[中文](README_zh-CN.md) | [English](README.md)

This tool uses the Lark Open Platform API to convert Lark (Feishu) documents to Markdown format, and also supports importing Markdown back into Lark documents.

## Prerequisites

1.  **Python 3.8+**
2.  **Lark App**: Create an app in the [Lark Developer Console](https://open.larksuite.com/app) and get the `App ID` and `App Secret`.
3.  **Permissions**: Ensure the app has the following scopes:
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
If you only need the export function, `docx:document:write_only` and `docx:document` permissions are not required.

## Installation

1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  Copy `env.example` to `.env`:
    ```bash
    cp env.example .env
    ```
2.  Edit `.env` and fill in your `FEISHU_APP_ID` and `FEISHU_APP_SECRET`.

## Usage

### Export (Lark -> Markdown)

Run the script using a Wiki Token or URL:

```bash
python scripts/main.py <WIKI_TOKEN_OR_URL>
```

Example:

```bash
python scripts/main.py wikcnAbc123Def456
# or
python scripts/main.py https://your-org.larksuite.com/wiki/wikcnAbc123Def456
```

The output is saved as `output.md` by default. You can specify the output file using the `-o` parameter:

```bash
python scripts/main.py <TOKEN> -o my_doc.md
```

### Import (Markdown -> Lark)

Import a Markdown file into an existing Lark document.

**Note:** The Lark bot must have **edit** permissions for the target document.

```bash
python scripts/main.py --import-file <MARKDOWN_FILE> <WIKI_TOKEN_OR_URL>
```

Example:

```bash
python scripts/main.py --import-file input.md https://your-org.larksuite.com/wiki/wikcnAbc123Def456
```

**Mermaid Support:**
The tool supports importing Mermaid diagrams (`mermaid` code blocks).
*   It automatically converts them into Lark's "Diagram" blocks.
*   **Tip:** If you encounter rendering issues, try manually creating a "Diagram" block in the target document first. The tool will automatically discover the correct component ID from it.

### Document Authorization

Before using this tool, you must grant the Lark bot access permissions to the document.

**Key Step:**
Please **share/send the Lark/Feishu document to a group chat that contains the Lark bot**.
*   This step automatically grants the bot read access to the document.
*   If you need to write/import Markdown to the document, ensure the bot has **edit** permissions.
*   If this step is skipped, the program may fail with "Permission Denied" or "Insufficient Permissions" errors.

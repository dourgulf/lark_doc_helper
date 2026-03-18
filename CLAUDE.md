# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp scripts/env.example scripts/.env
# Edit scripts/.env with FEISHU_APP_ID and FEISHU_APP_SECRET
```

### Run (from the `scripts/` directory)
```bash
# Export Lark doc → Markdown
python main.py <WIKI_TOKEN_OR_URL>
python main.py <TOKEN> -o output.md

# Import Markdown → Lark doc
python main.py --import-file input.md <WIKI_TOKEN_OR_URL>
```

### Tests (run from the `scripts/` directory since imports are relative)
```bash
cd scripts && python ../test/test_parser.py
cd scripts && python ../test/test_serialization.py
```

## Architecture

All source files live under `scripts/`. There is no package structure — files import each other directly by name, so tests and scripts must be run from within `scripts/`.

### Data Flow

**Export (Lark → Markdown):**
`main.py` → `FeishuClient.get_wiki_node_info()` → `FeishuClient.get_docx_blocks()` → `MarkdownConverter.convert()` → file

**Import (Markdown → Lark):**
`main.py` → scan existing blocks for Mermaid component ID → `MarkdownToLarkConverter.parse()` → `FeishuClient.create_blocks()` / `FeishuClient.create_table()`

### Key Files

- **`feishu_client.py`** — Wraps `lark-oapi` SDK. Handles pagination for block listing, multi-pass fetching for table cells (Table 31 → Row 32 → Cell 33 → Content), rate-limit delays, and the two-phase table creation workaround.
- **`converter.py`** (`MarkdownConverter`) — Converts Lark block objects (fetched from API) to Markdown. Handles block types by integer ID (2=Text, 3–11=Headings, 12=Bullet, 13=Ordered, 14=Code, 15=Quote, 22=Divider, 27=Image, 31=Table, 34=SyncedBlock, 40=AddOns/Mermaid).
- **`markdown_to_lark.py`** (`MarkdownToLarkConverter`) — Parses Markdown using `markdown-it-py` and builds Lark `Block` SDK objects. Tables require special handling: `_table_content_rows` is set as a private attribute on the table block and processed separately by `main.py`.
- **`main.py`** — CLI entry point. Resolves URL → wiki token → obj_token, orchestrates export or import, handles the table special-case loop.

### Critical Design Details

**Table creation workaround:** Creating nested Table→Row→Cell→Content in a single API call fails. Instead, `main.py` detects blocks with `_table_content_rows`, creates the table frame first, then fetches the auto-created rows/cells and fills them with content via `FeishuClient.create_table()`.

**Mermaid diagrams:** Lark represents Mermaid as AddOns blocks (type 40) with a `component_type_id`. This ID varies by Lark organization. The tool auto-discovers it by scanning existing blocks, falls back to `MERMAID_COMPONENT_TYPE_ID` in `.env`, or uses a hardcoded default (`blk_640017963d808005a21a6445`).

**Domain detection:** URLs containing `larksuite.com` use `lark_oapi.LARK_DOMAIN`; URLs containing `feishu.cn` use `lark_oapi.FEISHU_DOMAIN`. This must be passed when constructing `FeishuClient`.

**Block type map:** `CODE_LANGUAGE_MAP` in `converter.py` (ID→string) is the inverse of the one in `markdown_to_lark.py` (string→ID). Keep them in sync.

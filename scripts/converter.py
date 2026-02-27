import json
from lark_oapi.api.docx.v1.model import Block, Text, TextRun, MentionUser, MentionDoc

class MarkdownConverter:
    def __init__(self, blocks, image_handler=None):
        self.blocks = blocks
        self.image_handler = image_handler
        self.block_map = {b.block_id: b for b in blocks}
        self.children_map = {}
        for b in blocks:
            pid = b.parent_id
            if pid not in self.children_map:
                self.children_map[pid] = []
            self.children_map[pid].append(b)
        
    def convert(self):
        # The first block is typically the page root, but we can also find the one with empty parent_id or verify it's type 1
        root = None
        for b in self.blocks:
            if b.block_type == 1: # Page
                root = b
                break
        
        if not root:
            return ""
            
        return self._process_children(root.block_id)

    def _process_children(self, parent_id, indent_level=0):
        children = self.children_map.get(parent_id, [])
        result = []
        
        current_list_index = 1
        last_block_type = None
        
        for child in children:
            # Handle ordered list numbering
            if child.block_type == 13:
                if last_block_type != 13:
                    current_list_index = 1
                idx = current_list_index
                current_list_index += 1
            else:
                idx = 1
                
            last_block_type = child.block_type
            
            text = self._process_block(child, indent_level, list_index=idx)
            if text:
                result.append(text)
        return "\n\n".join(result)

    def _process_block(self, block, indent_level, list_index=1):
        content = ""
        # Handle different block types
        b_type = block.block_type
        
        if b_type == 2: # Text
            content = self._parse_text(block.text)
        elif 3 <= b_type <= 11: # Headings 1-9
            level = b_type - 2
            # The SDK uses specific attributes for each heading level (heading1, heading2, ...)
            heading_attr_name = f"heading{level}"
            heading_data = getattr(block, heading_attr_name, None)
            
            if heading_data:
                text = self._parse_text(heading_data)
                content = f"{'#' * level} {text}"
            else:
                content = f"<!-- Missing attribute {heading_attr_name} for block type {b_type} -->"
        elif b_type == 12: # Bullet
            text = self._parse_text(block.bullet)
            indent = "  " * indent_level
            content = f"{indent}- {text}"
            # Check for nested items
            children_content = self._process_children(block.block_id, indent_level + 1)
            if children_content:
                content += "\n" + children_content
        elif b_type == 13: # Ordered
            text = self._parse_text(block.ordered)
            indent = "  " * indent_level
            content = f"{indent}{list_index}. {text}"
            children_content = self._process_children(block.block_id, indent_level + 1)
            if children_content:
                content += "\n" + children_content
        elif b_type == 14: # Code
            # Map language ID to string
            # Mapping based on Feishu Open Platform documentation
            CODE_LANGUAGE_MAP = {
                1: "plaintext", 2: "abap", 3: "ada", 4: "apache", 5: "apex", 6: "assembly", 7: "bash",
                8: "csharp", 9: "cpp", 10: "c", 11: "cobol", 12: "css", 13: "coffeescript", 14: "d",
                15: "dart", 16: "delphi", 17: "django", 18: "dockerfile", 19: "erlang", 20: "fortran",
                21: "foxpro", 22: "go", 23: "groovy", 24: "html", 25: "htmlbars", 26: "http", 27: "haskell",
                28: "json", 29: "java", 30: "javascript", 31: "julia", 32: "kotlin", 33: "latex", 34: "lisp",
                35: "logo", 36: "lua", 37: "matlab", 38: "makefile", 39: "markdown", 40: "nginx",
                41: "objectivec", 42: "openedgeabl", 43: "php", 44: "perl", 45: "postscript",
                46: "powerbuilder", 47: "powershell", 48: "prolog", 49: "protobuf", 50: "python",
                51: "r", 52: "rpg", 53: "ruby", 54: "rust", 55: "sas", 56: "scss", 57: "sql", 58: "scala",
                59: "scheme", 60: "scratch", 61: "shell", 62: "swift", 63: "thrift", 64: "typescript",
                65: "vbscript", 66: "visualbasic", 67: "xml", 68: "yaml",
            }
            
            lang = "plaintext"
            if hasattr(block.code, 'style') and block.code.style:
                if hasattr(block.code.style, 'language'):
                    lang_id = block.code.style.language
                    lang = CODE_LANGUAGE_MAP.get(lang_id, "plaintext")
                elif hasattr(block.code.style, 'language_identifier'):
                    lang = block.code.style.language_identifier
            
            text = self._parse_text(block.code, plain=True)
            
            # Heuristic: If lang is protobuf but content looks like JSON, switch to JSON
            if lang == "protobuf" and text.strip().startswith("{"):
                lang = "json"
                
            content = f"```{lang}\n{text}\n```"
        elif b_type == 15: # Quote
            text = self._parse_text(block.quote)
            content = f"> {text}"
        elif b_type == 22: # Divider
            content = "---"
        elif b_type == 27: # Image
            token = block.image.token
            if self.image_handler:
                image_path = self.image_handler(token)
                content = f"![Image]({image_path})"
            else:
                content = f"![Image]({token})"
        elif b_type == 31: # Table
            # Handle Table block
            col_size = block.table.property.column_size if block.table and block.table.property else 0
            rows = self.children_map.get(block.block_id, [])
            table_lines = []
            
            current_row_cells = []
            current_width = 0
            is_first_row = True
            
            for row in rows:
                # Get children of the row (Cells or direct Content)
                row_children = self.children_map.get(row.block_id, [])
                
                for child in row_children:
                    # Extract cell content and span
                    span = 1
                    cell_text = ""
                    
                    if child.block_type == 33: # Cell
                        span = child.table_cell.col_span if child.table_cell else 1
                        # Process content inside the cell
                        cell_children = self.children_map.get(child.block_id, [])
                        
                        cell_text_parts = []
                        for c in cell_children:
                            part = self._process_block(c, 0)
                            if part:
                                cell_text_parts.append(part)
                                
                        cell_text = "<br>".join(cell_text_parts).strip().replace("\n", "<br>")
                    else:
                        # Direct content under Row (Treat as a cell)
                        span = 1
                        part = self._process_block(child, 0)
                        cell_text = part.strip().replace("\n", "<br>") if part else ""

                    # Add to buffer
                    current_row_cells.append(cell_text)
                    
                    # Handle merged cells (colspan)
                    for _ in range(span - 1):
                        current_row_cells.append("")
                    
                    current_width += span
                    
                    # Check if row is full
                    if col_size > 0 and current_width >= col_size:
                        # Flush row
                        table_lines.append("| " + " | ".join(current_row_cells) + " |")
                        
                        # Add separator after header (first logical row)
                        if is_first_row:
                            cols = len(current_row_cells)
                            table_lines.append("| " + " | ".join(["---"] * cols) + " |")
                            is_first_row = False
                        
                        current_row_cells = []
                        current_width = 0
            
            # Flush any remaining cells (if table structure is imperfect)
            if current_row_cells:
                 table_lines.append("| " + " | ".join(current_row_cells) + " |")
                 if is_first_row:
                    cols = len(current_row_cells)
                    table_lines.append("| " + " | ".join(["---"] * cols) + " |")
            
            content = "\n".join(table_lines)
        elif b_type == 34: # Synced Block
            # Synced Block is a container, process its children
            content = self._process_children(block.block_id, indent_level)
        elif b_type == 1: # Page
             content = self._process_children(block.block_id)
        elif b_type == 40: # Diagram / Embedded App (AddOns)
            content = "> 暂时无法在飞书文档外展示此内容"
            
            if hasattr(block, 'add_ons') and block.add_ons:
                 # Parse record JSON
                 record_json = getattr(block.add_ons, 'record', None)
                 if record_json:
                     try:
                         record_data = json.loads(record_json)
                         # Mermaid code is usually in 'data' field
                         mermaid_code = record_data.get('data', '')
                         if mermaid_code:
                             # Some cleaning might be needed (e.g., unicode escapes are handled by json.loads)
                             content = f"```mermaid\n{mermaid_code}\n```"
                     except json.JSONDecodeError:
                         # print(f"Warning: Failed to parse AddOn record JSON for block {block.block_id}")
                         pass
            
            # If no content found, content remains the placeholder
        else:
            # Fallback for unsupported types
            content = f"<!-- Unsupported block type: {b_type} -->"
            
        return content

    def _parse_text(self, text_body, plain=False):
        if not text_body or not text_body.elements:
            return ""
            
        result = []
        for element in text_body.elements:
            if element.text_run:
                text = element.text_run.content
                if not plain:
                    style = element.text_run.text_element_style
                    if style:
                        if style.bold:
                            text = f"**{text}**"
                        if style.italic:
                            text = f"*{text}*"
                        if style.strikethrough:
                            text = f"~~{text}~~"
                        if style.inline_code:
                            text = f"`{text}`"
                        if style.link:
                            url = style.link.url
                            text = f"[{text}]({url})"
                result.append(text)
            elif element.mention_user:
                result.append(f"@{element.mention_user.user_id}")
            elif element.mention_doc:
                result.append(f"[{element.mention_doc.title}]({element.mention_doc.url})")
                
        return "".join(result)

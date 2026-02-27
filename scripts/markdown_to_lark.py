import json
import os
import lark_oapi as lark
from lark_oapi.api.docx.v1.model import Block, Text, TextRun, TextStyle, TextElement, TextElementStyle, AddOns, Divider, Link, Table, TableProperty, TableCell
from markdown_it import MarkdownIt

# Inverted from converter.py
CODE_LANGUAGE_MAP = {
    "plaintext": 1, "abap": 2, "ada": 3, "apache": 4, "apex": 5, "assembly": 6, "bash": 7,
    "csharp": 8, "cpp": 9, "c": 10, "cobol": 11, "css": 12, "coffeescript": 13, "d": 14,
    "dart": 15, "delphi": 16, "django": 17, "dockerfile": 18, "erlang": 19, "fortran": 20,
    "foxpro": 21, "go": 22, "groovy": 23, "html": 24, "htmlbars": 25, "http": 26, "haskell": 27,
    "json": 28, "java": 29, "javascript": 30, "js": 30, "julia": 31, "kotlin": 32, "latex": 33, "lisp": 34,
    "logo": 35, "lua": 36, "matlab": 37, "makefile": 38, "markdown": 39, "nginx": 40,
    "objectivec": 41, "openedgeabl": 42, "php": 43, "perl": 44, "postscript": 45,
    "powerbuilder": 46, "powershell": 47, "prolog": 48, "protobuf": 49, "python": 50, "py": 50,
    "r": 51, "rpg": 52, "ruby": 53, "rust": 54, "sas": 55, "scss": 56, "sql": 57, "scala": 58,
    "scheme": 59, "scratch": 60, "shell": 61, "sh": 61, "swift": 62, "thrift": 63, "typescript": 64, "ts": 64,
    "vbscript": 65, "visualbasic": 66, "xml": 67, "yaml": 68,
}

# Placeholder for Mermaid Component Type ID
MERMAID_COMPONENT_TYPE_ID = os.getenv("MERMAID_COMPONENT_TYPE_ID", "blk_640017963d808005a21a6445") 

class MarkdownToLarkConverter:
    def __init__(self, markdown_content, mermaid_component_id=None):
        self.markdown_content = markdown_content
        self.blocks = []
        self.mermaid_component_id = mermaid_component_id or MERMAID_COMPONENT_TYPE_ID
        # Use default preset which includes most common features
        self.md = MarkdownIt('commonmark').enable('table').enable('strikethrough')
        
    def parse(self):
        print(f"[MarkdownToLark] Using Mermaid Component ID: {self.mermaid_component_id}")
        tokens = self.md.parse(self.markdown_content)
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == 'heading_open':
                level = int(token.tag[1:])
                # Next token should be inline
                if i + 1 < len(tokens) and tokens[i+1].type == 'inline':
                    text_elements = self._process_inline(tokens[i+1])
                    self.blocks.append(self._create_heading_block(text_elements, level))
                    i += 2 # Skip inline and heading_close
                else:
                    i += 1
                
            elif token.type == 'paragraph_open':
                # Next token should be inline
                if i + 1 < len(tokens) and tokens[i+1].type == 'inline':
                    text_elements = self._process_inline(tokens[i+1])
                    # Check if we are inside a list (handled by recursive structure in markdown-it? No, it's flat token stream)
                    # But we handle list items separately below.
                    # Wait, top-level paragraph?
                    # If the paragraph is inside a list item, we should have handled it in list_item logic?
                    # But markdown-it token stream is flat.
                    # list_item_open -> paragraph_open -> inline -> paragraph_close -> list_item_close
                    # So if I handle list logic by skipping tokens, I won't see this paragraph_open here.
                    # Correct.
                    
                    self.blocks.append(self._create_text_block(text_elements))
                    i += 2 # Skip inline and paragraph_close
                else:
                    i += 1
                    
            elif token.type == 'bullet_list_open':
                # We need to process list items
                i += 1
                while i < len(tokens) and tokens[i].type != 'bullet_list_close':
                    if tokens[i].type == 'list_item_open':
                        # Scan for content
                        j = i + 1
                        while j < len(tokens) and tokens[j].type != 'list_item_close':
                            if tokens[j].type == 'inline':
                                # Found content
                                text_elements = self._process_inline(tokens[j])
                                self.blocks.append(self._create_bullet_block(text_elements))
                            j += 1
                        i = j # Move to list_item_close
                    i += 1
                # i is at bullet_list_close
                
            elif token.type == 'ordered_list_open':
                i += 1
                while i < len(tokens) and tokens[i].type != 'ordered_list_close':
                    if tokens[i].type == 'list_item_open':
                        j = i + 1
                        while j < len(tokens) and tokens[j].type != 'list_item_close':
                            if tokens[j].type == 'inline':
                                text_elements = self._process_inline(tokens[j])
                                self.blocks.append(self._create_ordered_block(text_elements))
                            j += 1
                        i = j
                    i += 1
                    
            elif token.type == 'fence':
                lang = token.info.strip().split()[0] if token.info else 'plaintext'
                content = token.content
                if lang == 'mermaid':
                    self.blocks.append(self._create_mermaid_block(content))
                else:
                    self.blocks.append(self._create_code_block(content, lang))
                    
            elif token.type == 'blockquote_open':
                # Simplified: only take first paragraph in blockquote
                i += 1
                while i < len(tokens) and tokens[i].type != 'blockquote_close':
                    if tokens[i].type == 'inline':
                         text_elements = self._process_inline(tokens[i])
                         self.blocks.append(self._create_quote_block(text_elements))
                    i += 1
            
            elif token.type == 'hr':
                self.blocks.append(self._create_divider_block())

            elif token.type == 'table_open':
                table_block, next_index = self._process_table(tokens, i)
                if table_block:
                    self.blocks.append(table_block)
                i = next_index
                continue
            
            # Skip other tokens (like close tags if not handled, or unhandled types)
            i += 1
            
        return self.blocks

    def _process_table(self, tokens, start_index):
        # Parses table structure from token stream
        # table_open -> thead_open -> tr_open -> th_open -> inline -> th_close ... -> tr_close -> thead_close -> tbody_open ... -> table_close
        
        i = start_index + 1
        rows = []
        col_count = 0
        
        # We need to collect rows first, then build the Table Block
        
        current_row_cells = []
        in_thead = False
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == 'table_close':
                break
                
            elif token.type == 'thead_open':
                in_thead = True
            elif token.type == 'thead_close':
                in_thead = False
            
            elif token.type == 'tr_open':
                current_row_cells = []
            elif token.type == 'tr_close':
                # Create Row Block
                if not col_count:
                    col_count = len(current_row_cells)
                
                # Build Row Block with Children (Cells)
                # Note: We will attach this to the Table block for post-processing, 
                # but we won't send it in the initial create call.
                row_block = Block.builder().block_type(32).children(current_row_cells).build()
                # Manually set table_row property since SDK might be missing TableRow class or builder support
                # This is required for Type 32 blocks.
                row_block.table_row = {}
                
                rows.append(row_block)
                
            elif token.type == 'th_open' or token.type == 'td_open':
                # Find content
                content_elements = []
                j = i + 1
                while j < len(tokens):
                    if tokens[j].type == 'inline':
                        content_elements = self._process_inline(tokens[j])
                    elif tokens[j].type == 'th_close' or tokens[j].type == 'td_close':
                        i = j
                        break
                    j += 1
                
                # Create Cell Block
                # Cell contains Text Block (Paragraph)
                text_block = self._create_text_block(content_elements)
                
                # IMPORTANT: Try to add `table_cell` attribute again, but as an object.
                # Previous error: `Invalid parameter type in json: children` for ROW.
                # This means the ROW's children (CELLS) are invalid.
                # A Cell (33) MUST be valid.
                
                # Maybe the issue is that we are using `children([text_block])`?
                # Does Cell support children in creation? Yes.
                
                # Let's try adding `table_cell` property back. It might be required even if empty.
                cell_block = Block.builder().block_type(33).table_cell(
                    TableCell.builder().build()
                ).children([text_block]).build()
                
                current_row_cells.append(cell_block)
                
            i += 1
            
        # Create Table Block
        if not rows:
            return None, i
            
        # Calculate column width to occupy full width (approx 800-900 px/points)
        total_width = 850
        avg_width = int(total_width / col_count) if col_count > 0 else 100
        col_widths = [avg_width] * col_count
            
        table_block = Block.builder().block_type(31).table(
            Table.builder()
                .property(TableProperty.builder()
                    .column_size(col_count)
                    .row_size(len(rows))
                    .column_width(col_widths)
                    .build())
                .build()
        ).build()
        
        # Attach rows to the table block for post-processing in main.py
        table_block._table_content_rows = rows
        
        return table_block, i

    def _process_inline(self, token):
        elements = []
        children = token.children
        if not children:
            return elements
            
        current_style = {'bold': False, 'italic': False, 'strike': False, 'code': False, 'link': None}
        
        for child in children:
            if child.type == 'text':
                content = child.content
                style = self._build_style(current_style)
                elements.append(TextElement.builder().text_run(
                    TextRun.builder().content(content).text_element_style(style).build()
                ).build())
            elif child.type == 'code_inline':
                content = child.content
                style = self._build_style(current_style, force_code=True)
                elements.append(TextElement.builder().text_run(
                    TextRun.builder().content(content).text_element_style(style).build()
                ).build())
            elif child.type == 'strong_open':
                current_style['bold'] = True
            elif child.type == 'strong_close':
                current_style['bold'] = False
            elif child.type == 'em_open':
                current_style['italic'] = True
            elif child.type == 'em_close':
                current_style['italic'] = False
            elif child.type == 's_open':
                current_style['strike'] = True
            elif child.type == 's_close':
                current_style['strike'] = False
            elif child.type == 'link_open':
                href = child.attrGet('href')
                current_style['link'] = href
            elif child.type == 'link_close':
                current_style['link'] = None
            elif child.type == 'image':
                 # Fallback for image: just show alt text or url
                 content = f"![{child.content}]({child.attrGet('src')})"
                 elements.append(TextElement.builder().text_run(
                    TextRun.builder().content(content).build()
                 ).build())
                
        return elements

    def _build_style(self, style_dict, force_code=False):
        builder = TextElementStyle.builder()
        has_style = False
        if style_dict['bold']:
            builder.bold(True)
            has_style = True
        if style_dict['italic']:
            builder.italic(True)
            has_style = True
        if style_dict['strike']:
            builder.strikethrough(True)
            has_style = True
        if style_dict['code'] or force_code:
            builder.inline_code(True)
            has_style = True
        if style_dict['link']:
            builder.link(Link.builder().url(style_dict['link']).build())
            has_style = True
            
        return builder.build() if has_style else None

    def _create_block_base(self, block_type, data_key, data_obj):
        builder = Block.builder().block_type(block_type)
        if hasattr(builder, data_key):
            getattr(builder, data_key)(data_obj)
        else:
            block = builder.build()
            setattr(block, data_key, data_obj)
            return block
        return builder.build()

    def _create_text_payload(self, text_elements):
        return Text.builder().elements(text_elements).build()

    def _create_heading_block(self, text_elements, level):
        block_type = level + 2
        return self._create_block_base(block_type, f"heading{level}", self._create_text_payload(text_elements))

    def _create_text_block(self, text_elements):
        return self._create_block_base(2, "text", self._create_text_payload(text_elements))

    def _create_bullet_block(self, text_elements):
        return self._create_block_base(12, "bullet", self._create_text_payload(text_elements))

    def _create_ordered_block(self, text_elements):
        return self._create_block_base(13, "ordered", self._create_text_payload(text_elements))

    def _create_quote_block(self, text_elements):
        return self._create_block_base(15, "quote", self._create_text_payload(text_elements))

    def _create_divider_block(self):
        return Block.builder().block_type(22).divider(Divider.builder().build()).build()

    def _create_code_block(self, code_content, lang):
        lang_id = CODE_LANGUAGE_MAP.get(lang, 1)
        style = TextStyle.builder().language(lang_id).build()
        
        text_element = TextElement.builder().text_run(
            TextRun.builder().content(code_content).text_element_style(
                TextElementStyle.builder().build()
            ).build()
        ).build()
        
        code_data = Text.builder().style(style).elements([text_element]).build()
        return self._create_block_base(14, "code", code_data)

    def _create_mermaid_block(self, mermaid_code):
        record_data = {"data": mermaid_code}
        record_json = json.dumps(record_data, ensure_ascii=False)
        
        add_ons_data = AddOns.builder() \
            .component_type_id(self.mermaid_component_id) \
            .record(record_json) \
            .build()
            
        return self._create_block_base(40, "add_ons", add_ons_data)

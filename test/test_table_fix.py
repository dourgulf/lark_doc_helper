import sys
import os
import lark_oapi
from lark_oapi.api.docx.v1.model import Block, Table, TableCell

sys.path.append(os.path.join(os.getcwd(), 'scripts'))
from markdown_to_lark import MarkdownToLarkConverter

def test_table_row_size():
    md = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
"""
    converter = MarkdownToLarkConverter(md)
    blocks = converter.parse()
    
    table_blocks = [b for b in blocks if b.block_type == 31]
    if not table_blocks:
        print("FAIL: No table block found")
        return

    table = table_blocks[0]
    
    row_size = table.table.property.row_size
    col_size = table.table.property.column_size
    
    print(f"Table Properties - Rows: {row_size}, Cols: {col_size}")
    
    if row_size == 3:
        print("SUCCESS: Row size is correct (3).")
    else:
        print(f"FAIL: Expected row size 3, got {row_size}")

if __name__ == "__main__":
    test_table_row_size()

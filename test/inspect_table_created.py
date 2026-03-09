import os
from dotenv import load_dotenv
from feishu_client import FeishuClient
import lark_oapi

load_dotenv()
app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")
domain = lark_oapi.FEISHU_DOMAIN

client = FeishuClient(app_id, app_secret, domain=domain)
token = "FWOzw5YaQikI84kGyarlG8iWgSh"

# Get real token
node = client.get_wiki_node_info(token)
doc_token = node.obj_token
print(f"Doc Token: {doc_token}")

# List blocks
blocks = client.get_docx_blocks(doc_token)
print(f"Total blocks: {len(blocks)}")

# Find Table
for b in blocks:
    if b.block_type == 31:
        print(f"Table Block: {b.block_id}")
        print(f"  Row Size: {b.table.property.row_size}")
        print(f"  Col Size: {b.table.property.column_size}")
        
        # Check children
        # We need to find children with parent_id = b.block_id
        rows = [child for child in blocks if child.parent_id == b.block_id]
        print(f"  Found {len(rows)} rows (children).")
        
        for r in rows:
            print(f"    Row {r.block_id} (Type {r.block_type})")
            cells = [child for child in blocks if child.parent_id == r.block_id]
            print(f"      Found {len(cells)} cells.")
            for c in cells:
                content_blocks = [child for child in blocks if child.parent_id == c.block_id]
                print(f"        Cell {c.block_id}: Content blocks: {len(content_blocks)}")
                if content_blocks:
                    print(f"          Content Type: {content_blocks[0].block_type}")

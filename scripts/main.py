import os
import sys
import argparse
import lark_oapi
from dotenv import load_dotenv
from feishu_client import FeishuClient
from converter import MarkdownConverter
from markdown_to_lark import MarkdownToLarkConverter

def main():
    load_dotenv()
    
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET must be set in .env file")
        return

    parser = argparse.ArgumentParser(description="Convert Feishu Wiki to/from Markdown")
    parser.add_argument("token", help="The wiki token or URL (Source for export, Target for import)")
    parser.add_argument("--output", "-o", help="Output file path (for export)", default="output.md")
    parser.add_argument("--import-file", "-i", help="Input markdown file path (enable import mode)")
    
    args = parser.parse_args()
    
    token = args.token
    domain = None
    
    # Extract token if full URL is provided
    if "feishu.cn" in token or "larksuite.com" in token:
        if "larksuite.com" in token:
            domain = lark_oapi.LARK_DOMAIN
        elif "feishu.cn" in token:
            domain = lark_oapi.FEISHU_DOMAIN
            
        # Example: https://sample.feishu.cn/wiki/wikcnAbc123Def456
        token = token.split("/")[-1]
        # Remove query parameters if any
        if "?" in token:
            token = token.split("?")[0]
            
    print(f"Processing Wiki Token: {token}")
    
    try:
        client = FeishuClient(app_id, app_secret, domain=domain)
        
        # 1. Get Node Info to find the real object token and type
        print("Fetching node info...")
        node = client.get_wiki_node_info(token)
        
        obj_type = node.obj_type
        obj_token = node.obj_token
        title = node.title
        
        print(f"Found Node: {title} (Type: {obj_type})")
        
        if obj_type != "docx":
            print(f"Warning: Object type is '{obj_type}'. This tool is optimized for 'docx'.")

        # IMPORT MODE
        if args.import_file:
            print(f"Importing from {args.import_file} to Lark Document {obj_token}...")
            
            if not os.path.exists(args.import_file):
                print(f"Error: Input file {args.import_file} not found.")
                return

            with open(args.import_file, "r", encoding="utf-8") as f:
                md_content = f.read()
            
            # Scan existing blocks for Mermaid Component ID
            print("Scanning existing blocks for Mermaid configuration...")
            try:
                existing_blocks = client.get_docx_blocks(obj_token)
                mermaid_id = None
                for block in existing_blocks:
                    if block.block_type == 40 and hasattr(block, 'add_ons'):
                        # Found an AddOn block, assume it's Mermaid or compatible
                        # We could check 'record' content if needed, but ID is what we need
                        found_id = block.add_ons.component_type_id
                        print(f"Found existing AddOn/Mermaid block with ID: {found_id}")
                        mermaid_id = found_id
                        break
                
                if mermaid_id:
                    print(f"Using discovered Mermaid Component ID: {mermaid_id}")
                else:
                    print("No existing Mermaid blocks found. Using default ID.")
            except Exception as e:
                print(f"Warning: Failed to scan existing blocks: {e}")
                mermaid_id = None

            converter = MarkdownToLarkConverter(md_content, mermaid_component_id=mermaid_id)
            lark_blocks = converter.parse()
            
            print(f"Parsed {len(lark_blocks)} blocks from Markdown.")
            
            # Create blocks in the document
            # We append to the root block (which is the document itself, so parent_id = obj_token)
            print("Uploading blocks to Lark...")
            # Note: We should probably batch this if there are too many blocks, but for now sending all at once.
            # API limit might apply.
            
            # Create blocks
            created_blocks = client.create_blocks(obj_token, obj_token, lark_blocks)
            print(f"Successfully created {len(created_blocks)} blocks in document '{title}'.")
            
            # Check if any mermaid blocks were likely added
            has_mermaid = any(b.block_type == 40 for b in lark_blocks)
            if has_mermaid:
                print("\n[Note] Mermaid diagrams were imported.")
                print("       If they do not render correctly, please check the 'MERMAID_COMPONENT_TYPE_ID' in 'markdown_to_lark.py'.")
                print("       You may need to update it with the correct ID for your Lark organization.")
            
        # EXPORT MODE
        else:
            # 2. Fetch Blocks
            print(f"Fetching document blocks for object token: {obj_token}...")
            blocks = client.get_docx_blocks(obj_token)
            print(f"Retrieved {len(blocks)} blocks.")
            
            # 3. Convert
            print("Converting to Markdown...")
            converter = MarkdownConverter(blocks, image_handler=client.get_temp_download_url)
            md_content = converter.convert()
            
            # 4. Save
            output_path = args.output
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)
                
            print(f"Successfully saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
        if "permission denied" in str(e).lower():
            print("\n[Tip] Permission Denied detected. Please check:")
            print("1. Have you added the Bot to the Wiki/Document?")
            print("   (Open Doc -> Share/... -> Add App -> Select your Bot -> Read/Edit permission)")
            print("2. Are the API scopes enabled? (wiki:wiki:readonly, docx:document:readonly, docx:document:edit_as_app)")
            
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

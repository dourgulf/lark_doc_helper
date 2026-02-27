import os
from dotenv import load_dotenv
from feishu_client import FeishuClient
import json

def inspect_doc(token):
    load_dotenv()
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    
    if not app_id or not app_secret:
        print("Error: FEISHU_APP_ID and FEISHU_APP_SECRET must be set in .env file")
        return

    client = FeishuClient(app_id, app_secret, domain="https://open.larksuite.com") # Default to Larksuite based on user URL
    
    print(f"Inspecting Token: {token}")
    try:
        # 1. Get Node Info
        node = client.get_wiki_node_info(token)
        obj_token = node.obj_token
        print(f"Object Token: {obj_token}, Type: {node.obj_type}")
        
        # 2. Fetch Blocks
        blocks = client.get_docx_blocks(obj_token)
        print(f"Fetched {len(blocks)} blocks.")
        
        # 3. Search for Diagram/Mermaid blocks
        found = False
        for block in blocks:
            # Check for Diagram (Type 19) or Add-on (Type 40) or Code (Type 14)
            if block.block_type in [19, 40]: 
                print(f"\n[FOUND BLOCK] Type: {block.block_type}")
                print(f"Block ID: {block.block_id}")
                
                # Print attributes to see structure
                if block.block_type == 40: # Add-on
                    if hasattr(block, 'add_ons'):
                        print(f"Add-on Component ID: {block.add_ons.component_type_id}")
                        print(f"Add-on Record: {block.add_ons.record}")
                
                if block.block_type == 19: # Diagram
                    if hasattr(block, 'diagram'):
                         print(f"Diagram Type: {block.diagram.diagram_type}")
                
                # Try to dump the whole block object if possible (might need vars())
                try:
                    # Simple recursive dict dump
                    def obj_to_dict(obj):
                        if not hasattr(obj, "__dict__"):
                            return str(obj)
                        result = {}
                        for key, val in vars(obj).items():
                            if key.startswith("_"): continue
                            if isinstance(val, list):
                                result[key] = [obj_to_dict(i) for i in val]
                            elif hasattr(val, "__dict__"):
                                result[key] = obj_to_dict(val)
                            else:
                                result[key] = val
                        return result
                    
                    print("Full Block Structure:")
                    print(json.dumps(obj_to_dict(block), indent=2, ensure_ascii=False))
                    found = True
                except Exception as e:
                    print(f"Could not dump block: {e}")

        if not found:
            print("\nNo Diagram (19) or Add-on (40) blocks found in this document.")
            print("Please ensure the document actually HAS a Mermaid diagram created manually for reference.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Token from user's previous input
    inspect_doc("C3ubw9KAViGRR2kH4nel6Degguh") 

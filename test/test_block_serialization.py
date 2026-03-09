import json
import lark_oapi.api.docx.v1.model as model
from lark_oapi.core.json import JSON

def test_serialization():
    b = model.Block.builder().block_type(32).build()
    
    # Try to set unknown attribute
    b.table_row = {}
    
    # Serialize
    json_str = JSON.marshal(b)
    print(f"Serialized: {json_str}")
    
    if "table_row" in json_str:
        print("SUCCESS: table_row is present in JSON")
    else:
        print("FAIL: table_row is NOT present in JSON")

if __name__ == "__main__":
    test_serialization()

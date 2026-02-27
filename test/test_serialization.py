import json
from lark_oapi.api.docx.v1.model import Block, Text, TextRun, TextElement

def test_serialization():
    # 1. Create a Block using builder
    block = Block.builder().block_type(2).build()
    
    # 2. Manually set 'text' attribute
    text_element = TextElement.builder().text_run(
        TextRun.builder().content("Hello").build()
    ).build()
    text_obj = Text.builder().elements([text_element]).build()
    
    setattr(block, 'text', text_obj)
    
    # 3. Simulate serialization (Lark SDK uses a custom serializer usually, but let's check vars)
    print("Block dict:", block.__dict__)
    
    # Check if 'text' is in __dict__ or _text
    # The builder usually sets private attributes like '_text'
    
    # Let's see what attributes Block has
    print("Block attributes:", dir(block))
    
    # 4. Try to see if there is a 'text' property or attribute
    if hasattr(block, 'text'):
        print("Block has 'text' attribute")
    else:
        print("Block does NOT have 'text' attribute")
        
    # 5. Check if there is '_text'
    if hasattr(block, '_text'):
        print("Block has '_text' attribute")

test_serialization()

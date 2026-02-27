from markdown_to_lark import MarkdownToLarkConverter
import json

md_content = """# Heading 1
## Heading 2
Paragraph text with **bold** and *italic* and `code`.
- Bullet 1
- Bullet 2
1. Ordered 1
2. Ordered 2
> Quote block

```python
print("Hello")
```

```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```
"""

converter = MarkdownToLarkConverter(md_content)
blocks = converter.parse()

print(f"Parsed {len(blocks)} blocks.")
for i, block in enumerate(blocks):
    print(f"Block {i}: Type {block.block_type}")
    if block.block_type == 40: # AddOns
        print(f"  AddOns Component ID: {block.add_ons.component_type_id}")
        print(f"  Record: {block.add_ons.record}")
    elif block.block_type == 14: # Code
        print(f"  Code Language: {block.code.style.language}")
        # print content
        content = "".join([e.text_run.content for e in block.code.elements])
        print(f"  Code Content: {content}")

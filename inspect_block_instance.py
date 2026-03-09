import lark_oapi.api.docx.v1.model as model
import inspect

print("Attributes of Block instance:")
b = model.Block.builder().build()
print(dir(b))

print("\nIs table_row in Block?")
if hasattr(b, 'table_row'):
    print("Yes, table_row exists")
else:
    print("No, table_row does not exist")

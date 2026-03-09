import lark_oapi.api.docx.v1.model as model
import inspect

print("Attributes of TableProperty class:")
for name, obj in inspect.getmembers(model.TableProperty):
    if not name.startswith("_"):
        print(name)

print("\nAttributes of TablePropertyBuilder class:")
for name, obj in inspect.getmembers(model.TablePropertyBuilder):
    if not name.startswith("_"):
        print(name)

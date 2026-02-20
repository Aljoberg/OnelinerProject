import ast
from utils import Context, Handle, TransformFunc, generate_name


@Handle(ast.ClassDef)
def handle_classdef(node: ast.ClassDef, transform: TransformFunc, ctx: Context):
    class_name = node.name
    base_classes = [transform(base) for base in node.bases]
    
    class_dict_entries = []
    annotations_dict_entries = []
    
    for stmt in node.body:
        if isinstance(stmt, ast.FunctionDef):
            class_dict_entries.append(f"'{stmt.name}': {transform(stmt)}")
        elif isinstance(stmt, ast.AnnAssign) and stmt.simple:
            target = stmt.target
            if isinstance(target, ast.Name):
                annotations_dict_entries.append(f"'{target.id}': {transform(stmt.annotation)}")
                if stmt.value:
                    class_dict_entries.append(f"'{target.id}': {transform(stmt.value)}")
            elif isinstance(target, ast.Attribute):
                pass
    
    bases_str = ", ".join(base_classes) if base_classes else ""
    
    if class_dict_entries or annotations_dict_entries:
        ns_var = generate_name(prefix="__class_ns_")
        body_parts = []
        if annotations_dict_entries:
            body_parts.append(f"{ns_var}['__annotations__'] = {{{', '.join(annotations_dict_entries)}}}")
        for entry in class_dict_entries:
            body_parts.append(f"{ns_var}.update({{{entry}}})")
        
        exec_body_lambda = f"lambda {ns_var}: {'; '.join(body_parts)}"
        kwds_dict = "{'exec_body': " + exec_body_lambda + "}"
        cls = f"__import__('types').new_class({class_name!r}, ({bases_str}), {kwds_dict}, lambda {ns_var}: None)"
    else:
        cls = f"__import__('types').new_class({class_name!r}, ({bases_str}), {{}}, lambda ns: None)"
    
    for decorator in node.decorator_list:
        cls = f"({transform(decorator)})({cls})"
    
    return f"({class_name} := {cls})"


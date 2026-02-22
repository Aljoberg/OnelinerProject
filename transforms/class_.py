import ast
from utils import Context, Handle, Scope, TransformFunc, generate_name


@Handle(ast.ClassDef)
def handle_classdef(node: ast.ClassDef, transform: TransformFunc, ctx: Context):
    # TODO all statements that bind names should bind them to the class dict, not as direct assignments, and annotations should go into the __annotations__ dict in the class dict as well. also need to handle decorators

    prev_scope = ctx.scope
    prev_class_dict_var = ctx.class_dict_var

    ctx.scope = Scope.CLASS
    ctx.class_dict_var = generate_name(prefix="__class_dict_")

    bases = ", ".join(transform(base) for base in node.bases)
    if len(node.bases) == 1:
        bases += ","
    
    kwds = {keyword.arg: transform(keyword.value) for keyword in node.keywords}
    kwds_code = ", ".join(f"{key!r}: {value}" for key, value in kwds.items())

    ctx.scope = prev_scope
    ctx.class_dict_var = prev_class_dict_var
    body = ", ".join(transform(stmt) for stmt in node.body)

    cls = f"__import__('types').new_class({node.name!r}, ({bases}), {{{kwds_code}}}, lambda {ctx.class_dict_var}: [{body}])"

    for decorator in node.decorator_list:
        cls = f"({transform(decorator)})({cls})"

    return f"({node.name} := {cls})"

    # class_name = node.name
    # base_classes = [transform(base) for base in node.bases]
    
    # class_dict_entries = []
    # annotations_dict_entries = []
    
    # for stmt in node.body:
    #     if isinstance(stmt, ast.FunctionDef):
    #         class_dict_entries.append(f"'{stmt.name}': {transform(stmt)}")
    #     elif isinstance(stmt, ast.AnnAssign) and stmt.simple:
    #         target = stmt.target
    #         if isinstance(target, ast.Name):
    #             annotations_dict_entries.append(f"'{target.id}': {transform(stmt.annotation)}")
    #             if stmt.value:
    #                 class_dict_entries.append(f"'{target.id}': {transform(stmt.value)}")
    #         elif isinstance(target, ast.Attribute):
    #             pass
    
    # bases_str = ", ".join(base_classes) if base_classes else ""
    
    # if class_dict_entries or annotations_dict_entries:
    #     ns_var = generate_name(prefix="__class_ns_")
    #     body_parts = []
    #     if annotations_dict_entries:
    #         body_parts.append(f"{ns_var}['__annotations__'] = {{{', '.join(annotations_dict_entries)}}}")
    #     for entry in class_dict_entries:
    #         body_parts.append(f"{ns_var}.update({{{entry}}})")
        
    #     exec_body_lambda = f"lambda {ns_var}: {'; '.join(body_parts)}"
    #     kwds_dict = "{'exec_body': " + exec_body_lambda + "}"
    #     cls = f"__import__('types').new_class({class_name!r}, ({bases_str}), {kwds_dict}, lambda {ns_var}: None)"
    # else:
    #     cls = f"__import__('types').new_class({class_name!r}, ({bases_str}), {{}}, lambda ns: None)"
    
    # for decorator in node.decorator_list:
    #     cls = f"({transform(decorator)})({cls})"
    
    # return f"({class_name} := {cls})"


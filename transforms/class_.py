import ast
from utils import Context, Handle, Scope, TransformFunc, ensure_assign, generate_name


@Handle(ast.ClassDef)
def handle_classdef(node: ast.ClassDef, transform: TransformFunc, ctx: Context):
    prev_scope = ctx.scope
    prev_class_dict_var = ctx.class_dict_var

    ctx.scope = Scope.CLASS
    ctx.class_dict_var = generate_name(prefix="__class_dict_")

    bases = ", ".join(transform(base) for base in node.bases)
    if len(node.bases) == 1:
        bases += ","
    
    kwds = {keyword.arg: transform(keyword.value) for keyword in node.keywords}
    kwds_code = ", ".join(f"{key!r}: {value}" for key, value in kwds.items())

    body = ", ".join(transform(stmt) for stmt in node.body)

    cls = f"__import__('types').new_class({node.name!r}, ({bases}), {{{kwds_code}}}, lambda {ctx.class_dict_var}: [{body}])"

    for decorator in node.decorator_list:
        cls = f"({transform(decorator)})({cls})"

    ctx.scope = prev_scope
    ctx.class_dict_var = prev_class_dict_var

    return ensure_assign(node.name, cls, ctx)
    # return f"({node.name} := {cls})"


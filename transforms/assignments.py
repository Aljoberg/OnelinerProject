import ast
from utils import Handle, TransformFunc, generate_name, Context, has_node


_AUG_OP_MAP = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.MatMult: "@",
    ast.Div: "/",
    ast.Mod: "%",
    ast.Pow: "**",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.BitAnd: "&",
    ast.FloorDiv: "//",
}


@Handle(ast.Assign)
def handle_assign(node: ast.Assign, transform: TransformFunc, ctx):
    ctx.assignment_temp_vars.clear()  # clear temp vars for this assignment
    value = transform(node.value)
    if all(not isinstance(i, (ast.Tuple, ast.List)) for i in node.targets):
        # no unpacking
        if len(node.targets) == 1:
            target = transform(node.targets[0])
            return f"({target} := {value})"
        else:
            tmp_val = generate_name(prefix="__assign_tmp_")
            return f"[({tmp_val} := {value}), " + ", ".join(f"({transform(t)} := {tmp_val})]" for t in node.targets)
    else:
        # god damnit
        if len(node.targets) == 1:
            
        has_walrus = has_node(node, ast.NamedExpr)
    

# @Handle(ast.AugAssign)
# def handle_aug_assign(node: ast.AugAssign, transform: TransformFunc, ctx):
#     return NotImplemented # TODO implement this

# @Handle(ast.AnnAssign)
# def handle_ann_assign(node: ast.AnnAssign, transform: TransformFunc, ctx):
#     return NotImplemented # TODO implement this


@Handle(ast.NamedExpr)
def handle_named_expr(node: ast.NamedExpr, transform: TransformFunc, ctx):
    value = transform(node.value)
    target = transform(node.target)
    return f"({target} := {value})"


@Handle(ast.AugAssign)
def handle_aug_assign(node: ast.AugAssign, transform: TransformFunc, ctx: Context):
    target = transform(node.target)
    value = transform(node.value)
    op = _AUG_OP_MAP[type(node.op)]
    if isinstance(node.target, ast.Attribute):
        return f"setattr({node.target.value.id}, {node.target.attr!r}, {target} {op} ({value}))"
    return f"({target} := {target} {op} {value})"


@Handle(ast.Delete)
def handle_delete(node: ast.Delete, transform: TransformFunc, ctx: Context):
    items = ", ".join(
        f"({transform(i)})"
        for i in node.targets
    )
    return f"exec({repr(f'del {items}')}, globals(), locals())"

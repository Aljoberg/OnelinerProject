import ast
from utils import Handle, TransformFunc, generate_name, Context, has_node


# _AUG_OP_MAP = {
#     ast.Add: "+",
#     ast.Sub: "-",
#     ast.Mult: "*",
#     ast.MatMult: "@",
#     ast.Div: "/",
#     ast.Mod: "%",
#     ast.Pow: "**",
#     ast.LShift: "<<",
#     ast.RShift: ">>",
#     ast.BitOr: "|",
#     ast.BitXor: "^",
#     ast.BitAnd: "&",
#     ast.FloorDiv: "//",
# }

def choose_assign(node: ast.Name | ast.Attribute | ast.Subscript, value: str, transform: TransformFunc):
    # i hope that's all of them
    if isinstance(node, ast.Name):
        return f"{transform(node)} := {value}"
    elif isinstance(node, ast.Attribute):
        return f"setattr({transform(node.value)}, {node.attr!r}, {value})"
    elif isinstance(node, ast.Subscript):
        return f"{transform(node.value)}.__setitem__({transform(node.slice)!r}, {value})"
    else:
        raise SyntaxError("????")

@Handle(ast.Assign)
def handle_assign(node: ast.Assign, transform: TransformFunc, ctx):
    ctx.assignment_temp_vars.clear()  # clear temp vars for this assignment
    value = transform(node.value)
    if all(not isinstance(i, (ast.Tuple, ast.List)) for i in node.targets):
        # no unpacking
        if len(node.targets) == 1:
            target = transform(node.targets[0])
            return "(" + choose_assign(target, value, transform) + ")"

        tmp_val = generate_name(prefix="__assign_tmp_")
        return f"[({tmp_val} := {value}), {', '.join(choose_assign(t, tmp_val, transform) for t in node.targets)}]"
    else:
        # god damnit
        out = []
        has_walrus = has_node(node, ast.NamedExpr)
        if has_walrus or len(node.targets) > 1:
            tmp_val = generate_name(prefix="__assign_tmp_")
            out.append(f"({tmp_val} := {value})")
        else:
            tmp_val = value

        for target in node.targets:
            unpacked = transform(target)
            names = ", ".join(choose_assign(var, mangled, transform) for var, mangled in ctx.assignment_temp_vars.items())

            out.append(f"[{names}] for {unpacked} in {tmp_val}]")

        return f"[{', '.join(out)}]"

@Handle(ast.AugAssign)
def handle_aug_assign(node: ast.AugAssign, transform: TransformFunc, ctx: Context):
    # name = name op value
    assignment = ast.Assign(
        targets=[node.target],
        value=ast.BinOp(
            left=node.target,
            op=node.op,
            right=node.value
        )
    )
    return transform(assignment)
#     return NotImplemented # TODO implement this

# @Handle(ast.AnnAssign)
# def handle_ann_assign(node: ast.AnnAssign, transform: TransformFunc, ctx):
#     return NotImplemented # TODO implement this


@Handle(ast.NamedExpr)
def handle_named_expr(node: ast.NamedExpr, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    target = transform(node.target)
    return f"({target} := {value})"


# @Handle(ast.AugAssign)
# def handle_aug_assign(node: ast.AugAssign, transform: TransformFunc, ctx: Context):
#     target = transform(node.target)
#     value = transform(node.value)
#     op = _AUG_OP_MAP[type(node.op)]
#     if isinstance(node.target, ast.Attribute):
#         return f"setattr({node.target.value.id}, {node.target.attr!r}, {target} {op} ({value}))"
#    return f"({target} := {target} {op} {value})"


@Handle(ast.Delete)
def handle_delete(node: ast.Delete, transform: TransformFunc, ctx: Context):
    items = ", ".join(
        f"({transform(i)})"
        for i in node.targets
    )
    return f"exec({repr(f'del {items}')}, globals(), locals())"

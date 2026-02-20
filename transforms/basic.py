import ast
from utils import Context, Handle, Pure, TransformFunc, generate_name

@Pure
@Handle(ast.Expr)
def handle_expr(node: ast.Expr, transform: TransformFunc, ctx: Context):
    return transform(node.value)

@Pure
@Handle(ast.Name)
def handle_name(node: ast.Name, transform: TransformFunc, ctx: Context):
    if isinstance(node.ctx, ast.Store):
        mangled_name = generate_name(prefix=f"__temp_assigment__{node.id}__")
        ctx.assignment_temp_vars[node.id] = mangled_name
        return mangled_name
    return node.id


@Handle(ast.Subscript)
def handle_subscript(node: ast.Subscript, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    slice_ = transform(node.slice)
    return f"{value}[{slice_}]"


@Handle(ast.Attribute)
def handle_attribute(node: ast.Attribute, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    attr = node.attr
    return f"{value}.{attr}"

@Pure
@Handle(ast.Pass)
def handle_pass(node: ast.Pass, transform: TransformFunc, ctx: Context):
    return "None" # or 0, or something


@Handle(ast.Yield, ast.YieldFrom)
def handle_yield(node: ast.Yield | ast.YieldFrom, transform: TransformFunc, ctx: Context):
    keyword = "yield from" if isinstance(node, ast.YieldFrom) else "yield"
    if node.value:
        value = transform(node.value)
        return f"({keyword} {value})"
    else:
        return f"({keyword})"


@Pure
@Handle(ast.Slice)
def handle_slice(node: ast.Slice, transform: TransformFunc, ctx: Context):
    start = transform(node.lower) if node.lower else ""
    stop = transform(node.upper) if node.upper else ""
    step = transform(node.step) if node.step else ""
    if isinstance(node.parent.ctx, ast.Store):
        return repr(slice(start, stop, step))
    if step:
        return f"{start}:{stop}:{step}"
    else:
        return f"{start}:{stop}"


@Handle(ast.Global)
def handle_global(node: ast.Global, transform: TransformFunc, ctx: Context):
    ctx.global_vars.update(node.names)
    return "None"


@Handle(ast.Nonlocal)
def handle_nonlocal(node: ast.Nonlocal, transform: TransformFunc, ctx: Context):
    ctx.nonlocal_vars.update(node.names)
    return ", ".join(node.names)
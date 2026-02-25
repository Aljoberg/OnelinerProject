import ast
from utils import Context, Handle, Pure, TransformFunc, generate_name

@Handle(ast.Expr)
@Pure
def handle_expr(node: ast.Expr, transform: TransformFunc, ctx: Context):
    return transform(node.value)

@Handle(ast.Name)
@Pure
def handle_name(node: ast.Name, transform: TransformFunc, ctx: Context):
    if isinstance(node.ctx, ast.Store) and node not in ctx.assignment_temp_vars:
        mangled_name = generate_name(prefix=f"__temp_assigment__{node.id}__")
        print("added to names", node, ctx.assignment_temp_vars)
        ctx.assignment_temp_vars[node] = mangled_name
        return mangled_name
    return node.id


@Handle(ast.Subscript)
def handle_subscript(node: ast.Subscript, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    slice_ = transform(node.slice)
    if isinstance(node.ctx, ast.Store) and node not in ctx.assignment_temp_vars:
        mangled_name = generate_name(prefix=f"__temp_subscript_assignment__{value}_{slice_}__")
        ctx.assignment_temp_vars[node] = mangled_name
        return mangled_name
    return f"{value}[{slice_}]"


@Handle(ast.Attribute)
def handle_attribute(node: ast.Attribute, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    attr = node.attr
    if isinstance(node.ctx, ast.Store) and node not in ctx.assignment_temp_vars:
        mangled_name = generate_name(prefix=f"__temp_attr_assignment__{value}_{attr}__")
        ctx.assignment_temp_vars[node] = mangled_name
        return mangled_name
    return f"{value}.{attr}"

@Handle(ast.Pass)
@Pure
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


@Handle(ast.Slice)
@Pure
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

import ast
from utils import Context, CurrentFunction, Handle, Scope, TransformFunc, generate_name, has_node


@Handle(ast.FunctionDef, ast.AsyncFunctionDef)
def handle_function_def(
    node: ast.FunctionDef | ast.AsyncFunctionDef, transform: TransformFunc, ctx: Context
):
    # Register global/nonlocal tracking for this function
    prev_current_function = ctx.current_function
    prev_scope = ctx.scope

    ctx.current_function = CurrentFunction(name=node.name, has_return=has_node(node, ast.Return))
    
    if ctx.current_function.has_return:
        ctx.current_function.return_store_var = generate_name(prefix="__return_store_")
        ctx.current_function.return_hit_var = generate_name(prefix="__return_hit_")
    
    ctx.scope = Scope.FUNCTION
    
    vararg = f"*{node.args.vararg.arg}" if node.args.vararg else ""
    kwarg = f"**{node.args.kwarg.arg}" if node.args.kwarg else ""
    
    
    body_statements = [transform(stmt) for stmt in node.body]
    body = ", ".join(body_statements)
    
    pos_args = ", ".join(
        f"{arg.arg}{f'={transform(val)}' if val else ''}"
        for arg, val in zip(
            node.args.args,
            [None] * (len(node.args.args) - len(node.args.defaults)) + node.args.defaults
        )
    )

    kw_args = ", ".join(
        f"{arg.arg}{f'={transform(val)}' if val else ''}"
        for arg, val in zip(node.args.kwonlyargs, node.args.kw_defaults)
    )

    pos_args = ", ".join(filter(None, [pos_args, vararg, kw_args, kwarg]))
    # if vkwargs:
    #     pos_args = pos_args + (", " if pos_args else "") + ", ".join(vkwargs)

    annotations = {}
    for arg in node.args.args + [node.args.vararg] + node.args.kwonlyargs + [node.args.kwarg]:
        if arg and arg.annotation:
            annotations[arg.arg] = transform(arg.annotation)
    if node.returns:
        annotations["return"] = transform(node.returns)
    
    is_async = isinstance(node, ast.AsyncFunctionDef)
    toggle_async = ""
    if is_async:
        code_var = generate_name(prefix="__async_function_")
        toggle_async = f"setattr({node.name}, '__code__', ({code_var} := {node.name}.__code__).replace(co_flags={code_var}.co_flags & ~32 | 128))"

    annotations_code = ""
    if annotations:
        annotations_code = f"{node.name}.__annotations__.update({{{', '.join(f'{key!r}: {value}' for key, value in annotations.items())}}})"
    
    return_store = f"({ctx.current_function.return_store_var} := [None]), ({ctx.current_function.return_hit_var} := False), " if ctx.current_function.has_return else ""
    body_code = f"[{return_store}{body}{f', {ctx.current_function.return_store_var}[0]' if ctx.current_function.has_return else ', None'}][-1]"
    func_expression = f"lambda{(' ' + pos_args) if pos_args else ''}: {body_code}"
    
    for decorator in node.decorator_list:
        func_expression = f"({transform(decorator)})({func_expression})"
    
    final_expr = ', '.join(filter(None, [func_expression, toggle_async, annotations_code]))

    ctx.current_function = prev_current_function
    ctx.scope = prev_scope
    
    if ctx.scope == Scope.CLASS:
        return f"{ctx.class_dict_var}.update({{{node.name!r}: {final_expr}}}) or ({node.name} := {final_expr})"
    return f"({node.name} := {final_expr})"


@Handle(ast.Return)
def handle_return(node: ast.Return, transform: TransformFunc, ctx: Context):
    if ctx.scope == Scope.FUNCTION:
        if node.value:
            value = transform(node.value)
            return f"({ctx.current_function.return_store_var}.__setitem__(0, {value}) or ({ctx.current_function.return_hit_var} := True))"
        else:
            return f"({ctx.current_function.return_hit_var} := True)"
    else:
        raise SyntaxError("Return statement outside of function")


@Handle(ast.Lambda)
def handle_lambda(node: ast.Lambda, transform: TransformFunc, ctx: Context):
    prev_scope = ctx.scope
    ctx.scope = Scope.FUNCTION
    vararg = f"*{node.args.vararg.arg}" if node.args.vararg else ""
    kwarg = f"**{node.args.kwarg.arg}" if node.args.kwarg else ""
    
    
    body_statements = transform(node.body)
    body = ", ".join(body_statements)
    
    pos_args = ", ".join(
        f"{arg.arg}{f'={transform(val)}' if val else ''}"
        for arg, val in zip(
            node.args.args,
            [None] * (len(node.args.args) - len(node.args.defaults)) + node.args.defaults
        )
    )

    kw_args = ", ".join(
        f"{arg.arg}{f'={transform(val)}' if val else ''}"
        for arg, val in zip(node.args.kwonlyargs, node.args.kw_defaults)
    )

    pos_args = ", ".join([pos_args, vararg, kw_args, kwarg])

    ctx.scope = prev_scope
    
    return f"(lambda {pos_args}: {body})"


@Handle(ast.Await)
def handle_await(node: ast.Await, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    return f"(yield from {value})"

@Handle(ast.Call)
def handle_call(node: ast.Call, transform: TransformFunc, ctx: Context):
    func = transform(node.func)
    args = ", ".join(transform(arg) for arg in node.args)
    keywords = ", ".join(f"{kw.arg}={transform(kw.value)}" if kw.arg else f"**{transform(kw.value)}" for kw in node.keywords)
    all_args = ", ".join(filter(None, [args, keywords]))
    return f"{func}({all_args})"
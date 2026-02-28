import ast
from utils import Context, Handle, Pure, TransformFunc


@Handle(ast.Constant)
@Pure
def handle_constant(node: ast.Constant, transform: TransformFunc, ctx: Context):
    return repr(node.value)


@Handle(ast.List)
@Pure
def handle_list(node: ast.List, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    return f"[{elts}]"


@Handle(ast.Tuple)
@Pure
def handle_tuple(node: ast.Tuple, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    if len(node.elts) == 1:
        elts += ","
    return f"({elts})"


@Handle(ast.Dict)
@Pure
def handle_dict(node: ast.Dict, transform: TransformFunc, ctx: Context):
    items = ", ".join(
        f"{transform(k)}: {transform(v)}" if k else f"**{transform(v)}"
        for k, v in zip(node.keys, node.values)
    )
    return f"{{{items}}}"


@Handle(ast.Set)
@Pure
def handle_set(node: ast.Set, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    return f"{{{elts}}}"


# why is this in literals lol
@Handle(ast.comprehension)
@Pure
def handle_comprehension(
    node: ast.comprehension, transform: TransformFunc, ctx: Context
):
    prev_should = ctx.should_assign_nonnames_to_temp
    prev_names = ctx.should_assign_names
    ctx.should_assign_nonnames_to_temp = False
    ctx.should_assign_names = False

    target = transform(node.target)

    ctx.should_assign_nonnames_to_temp = prev_should
    ctx.should_assign_names = prev_names

    iter_ = transform(node.iter)
    ifs = " ".join(f"if {transform(iff)}" for iff in node.ifs)
    return f"for {target} in {iter_}{' ' + ifs if ifs else ''}"


@Handle(ast.GeneratorExp, ast.ListComp, ast.SetComp)
@Pure
def handle_generator_exp(
    node: ast.GeneratorExp | ast.ListComp | ast.SetComp,
    transform: TransformFunc,
    ctx: Context,
):
    prev_in_loop = ctx.in_loop
    ctx.in_loop = True

    elt = transform(node.elt)
    comprehensions = " ".join(transform(comp) for comp in node.generators)

    brackets = (
        "[]"
        if isinstance(node, ast.ListComp)
        else "()" if isinstance(node, ast.GeneratorExp) else "{}"
    )

    ctx.in_loop = prev_in_loop

    return f"{brackets[0]}{elt} {comprehensions}{brackets[1]}"


@Handle(ast.DictComp)
@Pure
def handle_dict_comp(
    node: ast.DictComp,
    transform: TransformFunc,
    ctx: Context,
):
    prev_in_loop = ctx.in_loop
    ctx.in_loop = True

    key = transform(node.key)
    value = transform(node.value)
    comprehensions = " ".join(transform(comp) for comp in node.generators)

    ctx.in_loop = prev_in_loop

    return f"{{{key}: {value} {comprehensions}}}"


def _handle_format_spec(node: ast.JoinedStr, transform: TransformFunc) -> str:
    parts = []
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            value = part.value
            value = value.replace("\\", "\\\\")
            value = value.replace("'", "\\'")
            value = value.replace('"', '\\"')
            value = value.replace("\n", "\\n")
            parts.append(value)
        elif isinstance(part, ast.FormattedValue):
            parts.append(_handle_formatted_value_inner(part, transform))
        else:
            raise ValueError(f"Unexpected node inside JoinedStr: {type(part).__name__}")
    return "".join(parts)


def _handle_formatted_value_inner(
    node: ast.FormattedValue, transform: TransformFunc
) -> str:
    expr = transform(node.value)
    if expr.startswith("{"):
        expr = f" {expr}"

    result = f"{{{expr}"

    if node.conversion != -1:
        result += f"!{chr(node.conversion)}"

    if node.format_spec:
        format_spec = _handle_format_spec(node.format_spec, transform)
        result += f":{format_spec}"

    result += "}"
    return result


@Handle(ast.JoinedStr)
@Pure
def handle_joined_str(node: ast.JoinedStr, transform: TransformFunc, ctx: Context):
    parts = []
    for part in node.values:
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            value = part.value.replace("{", "{{").replace("}", "}}")
            parts.append(value)
        elif isinstance(part, ast.FormattedValue):
            parts.append(_handle_formatted_value_inner(part, transform))
        else:
            raise ValueError(f"Unexpected node inside JoinedStr: {type(part).__name__}")
    # return f'f"{parts[0]}"' if len(parts) == 1 else f'f"{"".join(parts)}"'
    return f'f"{"".join(parts)}"'


@Handle(ast.FormattedValue)
@Pure
def handle_formatted_value(
    node: ast.FormattedValue, transform: TransformFunc, ctx: Context
):
    return _handle_formatted_value_inner(node, transform)

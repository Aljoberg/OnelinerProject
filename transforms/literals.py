import ast
from utils import Context, Handle, Pure, TransformFunc


@Pure
@Handle(ast.Constant)
def handle_constant(node: ast.Constant, transform: TransformFunc, ctx: Context):
    return repr(node.value)


@Pure
@Handle(ast.List)
def handle_list(node: ast.List, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    return f"[{elts}]"


@Pure
@Handle(ast.Tuple)
def handle_tuple(node: ast.Tuple, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    if len(node.elts) == 1:
        elts += ","
    return f"({elts})"


@Pure
@Handle(ast.Dict)
def handle_dict(node: ast.Dict, transform: TransformFunc, ctx: Context):
    items = ", ".join(
        f"{transform(k)}: {transform(v)}" if k else f"**{transform(v)}" for k, v in zip(node.keys, node.values)
    )
    return f"{{{items}}}"


@Pure
@Handle(ast.Set)
def handle_set(node: ast.Set, transform: TransformFunc, ctx: Context):
    elts = ", ".join(transform(elt) for elt in node.elts)
    return f"{{{elts}}}"


@Pure
@Handle(ast.comprehension)
def handle_comprehension(
    node: ast.comprehension, transform: TransformFunc, ctx: Context
):
    target = transform(node.target)
    iter_ = transform(node.iter)
    ifs = " ".join(f"if {transform(iff)}" for iff in node.ifs)
    return f"for {target} in {iter_} {ifs}"


@Pure
@Handle(ast.GeneratorExp, ast.ListComp, ast.SetComp)
def handle_generator_exp(
    node: ast.GeneratorExp | ast.ListComp | ast.SetComp,
    transform: TransformFunc,
    ctx: Context,
):
    elt = transform(node.elt)
    comprehensions = " ".join(transform(comp) for comp in node.generators)

    brackets = (
        "[]"
        if isinstance(node, ast.ListComp)
        else "()" if isinstance(node, ast.GeneratorExp) else "{}"
    )

    return f"{brackets[0]}{elt} {comprehensions}{brackets[1]}"


@Pure
@Handle(ast.DictComp)
def handle_dict_comp(
    node: ast.DictComp,
    transform: TransformFunc,
    ctx: Context,
):
    key = transform(node.key)
    value = transform(node.value)
    comprehensions = " ".join(transform(comp) for comp in node.generators)
    return f"{{{key}: {value} {comprehensions}}}"


@Pure
@Handle(ast.JoinedStr)
def handle_joined_str(node: ast.JoinedStr, transform: TransformFunc, ctx: Context):
    parts = []
    for part in node.values:
        if isinstance(part, ast.Constant):
            parts.append(repr(part.s))
        elif isinstance(part, ast.FormattedValue):
            expr = transform(part.value)
            if part.format_spec:
                format_spec = transform(part.format_spec)
                parts.append(f"str({expr}).format({format_spec})")
            else:
                parts.append(f"str({expr})")
        else:
            raise TypeError(f"Unsupported type for JoinedStr part: {type(part).__name__}")
    return " + ".join(parts)


@Pure
@Handle(ast.FormattedValue)
def handle_formatted_value(node: ast.FormattedValue, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    if node.format_spec:
        format_spec = transform(node.format_spec)
        return f"format({value}, {format_spec})"
    else:
        return f"{value}"

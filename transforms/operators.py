import ast
from utils import Context, Handle, Pure, TransformFunc

_BIN_OP_MAP: dict[type[ast.AST], str] = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Pow: "**",
    ast.Mult: "*",
    ast.Div: "/",
    ast.FloorDiv: "//",
    ast.Mod: "%",
    ast.MatMult: "@",
    ast.LShift: "<<",
    ast.RShift: ">>",
    ast.BitOr: "|",
    ast.BitXor: "^",
    ast.BitAnd: "&",
}

_COMP_OP_MAP: dict[type[ast.AST], str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "in",
    ast.NotIn: "not in",
}

_UNARY_OP_MAP: dict[type[ast.AST], str] = {
    ast.UAdd: "+",
    ast.USub: "-",
    ast.Invert: "~",
    ast.Not: "not",
}


@Handle(*_BIN_OP_MAP.keys())
@Pure
def bin_op(node: ast.AST, transform: TransformFunc, ctx: Context):
    return _BIN_OP_MAP[type(node)]


@Handle(*_COMP_OP_MAP.keys())
@Pure
def comp_op(node: ast.AST, transform: TransformFunc, ctx: Context):
    return _COMP_OP_MAP[type(node)]


@Handle(*_UNARY_OP_MAP.keys())
@Pure
def unary_op(node: ast.AST, transform: TransformFunc, ctx: Context):
    return _UNARY_OP_MAP[type(node)]


@Handle(ast.BinOp)
def handle_bin_op(node: ast.BinOp, transform: TransformFunc, ctx: Context):
    left = transform(node.left)
    op = transform(node.op)
    right = transform(node.right)
    return f"({left} {op} {right})"  # TODO parenthesize only when necessary


@Handle(ast.Compare)
def handle_compare(node: ast.Compare, transform: TransformFunc, ctx: Context):
    left = transform(node.left)
    comparisons = []
    for op, comparator in zip(node.ops, node.comparators):
        op_str = transform(op)
        comp_str = transform(comparator)
        comparisons.append(f"{op_str} {comp_str}")
    return f"({left} {' '.join(comparisons)})"  # TODO parenthesize only when necessary


@Handle(ast.UnaryOp)
def handle_unary_op(node: ast.UnaryOp, transform: TransformFunc, ctx: Context):
    op_str = transform(node.op)
    operand_str = transform(node.operand)
    return f"({op_str}{operand_str})"  # TODO parenthesize only when necessary

# maybe pure?
@Handle(ast.BoolOp)
def handle_bool_op(node: ast.BoolOp, transform: TransformFunc, ctx: Context):
    op_str = "and" if isinstance(node.op, ast.And) else "or"
    return f" {op_str} ".join(
        f"({transform(value)})" for value in node.values
    )  # TODO parenthesize only when necessary

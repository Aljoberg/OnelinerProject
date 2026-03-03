import ast, builtins
from .utils import (
    set_debug,
    add_forbidden_names,
    stmt_handlers,
    ctx,
)


def transform(
    node: ast.AST,
) -> str:

    if type(node) in stmt_handlers:
        return stmt_handlers[type(node)](node, transform, ctx)
    else:
        raise NotImplementedError(f"Node type {type(node)} not implemented.")


def annotate_parents(root):  # TODO get rid of this
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def code_to_oneliner(code, debug=False):
    global forbidden_names

    tree = ast.parse(code)
    print(ast.dump(tree, indent=2))
    annotate_parents(tree)
    forbidden_names = {
        (i.name if isinstance(i, ast.alias) else i.id)
        for i in ast.walk(tree)
        if isinstance(i, (ast.alias, ast.Name))
    }
    add_forbidden_names(*forbidden_names)
    set_debug(debug)
    transformed_statements = [transform(stmt) for stmt in tree.body]

    return f"({'\n'.join(transformed_statements)})"


from . import transforms

list([transforms])  # load the package


code = open("test_code.py", errors="ignore").read()

with open("output_code.py", "w") as f:
    f.write(code_to_oneliner(code))

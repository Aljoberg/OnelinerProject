"""Transform Python source and provide a command-line entry point."""

import argparse
import ast
from pathlib import Path
from threading import RLock

from .utils import add_forbidden_names, ctx, reset, set_debug, stmt_handlers
from . import transforms  # Register the AST handlers.


_transform_lock = RLock()


def transform(node: ast.AST) -> str:
    handler = stmt_handlers.get(type(node))
    if handler is None:
        raise NotImplementedError(f"Node type {type(node).__name__} not implemented.")
    return handler(node, transform, ctx)


def annotate_parents(root):
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            child.parent = node


def code_to_oneliner(code: str, debug: bool = False) -> str:
    """Return an expression that executes the supported statements in code."""
    # Handlers share mutable context; serialize calls and clean up after failures.
    with _transform_lock:
        reset()
        try:
            tree = ast.parse(code)
            compile(tree, "<input>", "exec")
            annotate_parents(tree)
            # Arguments, aliases, definitions, and captures are not ast.Name nodes.
            names = set()
            for node in ast.walk(tree):
                for _, value in ast.iter_fields(node):
                    values = value if isinstance(value, list) else [value]
                    names.update(v for v in values if isinstance(v, str) and v.isidentifier())
                if isinstance(node, ast.alias):
                    names.add(node.name.split(".")[0])
            add_forbidden_names(*names)
            set_debug(debug)
            statements = ["(" + transform(stmt) + ")" for stmt in tree.body]
            return "[" + ", ".join(statements) + "]"
        finally:
            reset()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert Python source to a one-liner.")
    parser.add_argument("input", nargs="?", type=Path, default=Path("test_code.py"))
    parser.add_argument("-o", "--output", type=Path, default=Path("output_code.py"))
    parser.add_argument("--debug", action="store_true", help="Use descriptive generated names")
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output must be different files")
    try:
        result = code_to_oneliner(args.input.read_text(encoding="utf-8"), debug=args.debug)
        compile(result, str(args.output), "exec")
        args.output.write_text(result + "\n", encoding="utf-8")
    except (OSError, UnicodeError, SyntaxError, NotImplementedError) as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()

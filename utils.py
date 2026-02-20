import ast
import itertools
import keyword
import string
from typing import Callable, TypeVar

from attr import dataclass

@dataclass
class CurrentFunction:
    name: str = ""
    has_return: bool = False
    return_hit_var: str = ""
    return_store_var: str = ""


class Context:
    in_loop = False
    continue_var = ""
    break_var = ""
    in_function = False
    current_function = CurrentFunction()  # same here
    global_vars = set[str]()
    nonlocal_vars = set[str]()
    assignment_temp_vars = dict[str, str]()  # maps variable names to their current temp var for assignment expressions


ctx = Context()  # maybe just use class attributes and not an instance

T = TypeVar("T", bound=ast.AST)

TransformFunc = Callable[[ast.AST], str]
HandleFunc = Callable[[T, TransformFunc, Context], str]

stmt_handlers: dict[type[ast.AST], HandleFunc] = {}


def has_node(node: ast.AST, target_type: type[ast.AST]):
    if isinstance(node, target_type):
        return True
    for child in ast.iter_child_nodes(node):
        if has_node(child, target_type):
            return True
    return False

def generate_name(prefix=""):
    return next(generate_names(prefix=prefix))



DEBUG = False  # for prefixes and logs, i suppose
forbidden_names = set()


def generate_names(n=1, prefix=""):
    possible_chars = string.ascii_letters
    for _ in range(n):
        name_generator = (
            "".join(name)
            for length in itertools.count(1)
            for name in itertools.product(possible_chars, repeat=length)
        )
        name = next(
            name
            for name in name_generator
            if name not in forbidden_names and not keyword.iskeyword(name)
        )
        forbidden_names.add(name)
        if DEBUG:
            yield prefix + name
        else:
            yield name


def prepend(contents: str):
    valooe = f"{ctx.current_function.return_hit_var} or "  # <3.12 moment
    # valooe_loop = f"not {current_loop_and_function[1]} and not {current_loop_and_function[2]} and "
    valooe_loop = f"any(({ctx.break_var}, {ctx.continue_var})) or "
    # input()
    return f'({valooe if ctx.current_function.has_return else ""}{valooe_loop if ctx.in_loop else ""}{contents})' if any((ctx.current_function.has_return, ctx.in_loop)) else contents


def Handle(*stmts: type[T]):
    def decorator(func: HandleFunc[T]):
        if not hasattr(func, "is_pure"):
            func.is_pure = False
        real_func = (
            func
            if func.is_pure
            else lambda *args, **kwargs: print("hi", args, kwargs) or prepend(func(*args, **kwargs))
        )
        for stmt in stmts:
            stmt_handlers[stmt] = real_func
        return real_func
    return decorator


def Pure(func: HandleFunc[T]):
    func.is_pure = True
    return func
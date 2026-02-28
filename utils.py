import ast
import enum
import itertools
import keyword
import string
from typing import Callable, TypeVar


from dataclasses import dataclass

class Scope(enum.Enum):
    MODULE = enum.auto()
    CLASS = enum.auto()
    FUNCTION = enum.auto()

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
    scope = Scope.MODULE
    current_function = CurrentFunction()  # same here
    class_dict_var = ""  # for class scope, holds the dict where we can store annotations and other class-level info
    global_vars = set[str]()
    nonlocal_vars = set[str]()
    assignment_temp_vars = dict[ast.Name, str]()  # maps variable names to their current temp var for assignment expressions
    should_assign_nonnames_to_temp = True
    should_assign_names = True
    # for_names = dict[ast.Name, str]()  # names that are otherwise only in the comprehension
    # in_for = False # TODO maybe just reuse assignment


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

def set_forbidden_names(*names: str): # this is weird
    print(names, "forbidden names")
    forbidden_names.update(names)

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
    valooe_loop = f"{ctx.continue_var} or "
    # input()
    return f'({valooe if ctx.current_function.has_return else ""}{valooe_loop if ctx.continue_var else ""}{contents})' if any((ctx.current_function.has_return, ctx.continue_var)) else contents


def Handle(*stmts: type[T]):
    def decorator(func: HandleFunc[T]):
        if not hasattr(func, "is_pure"):
            func.is_pure = False
        real_func = (
            func
            if func.is_pure
            else lambda *args, **kwargs: print("hi", args, kwargs) or prepend(func(*args, **kwargs)) # TODO cast type to TransformFunc
        )
        for stmt in stmts:
            stmt_handlers[stmt] = real_func
        return real_func
    return decorator


def Pure(func: HandleFunc[T]):
    func.is_pure = True
    return func

def ensure_assign(variable: str, value: str, ctx: Context, *, in_match=False):
    if ctx.scope == Scope.CLASS:
        return f"[({variable} := {value}), {ctx.class_dict_var}.update({{{variable!r}: {variable}}})]"
    else:
        if in_match:
            return f"[({variable} := {value})]"
        return f"({variable} := {value})"
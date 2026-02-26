import ast
from copy import deepcopy
from utils import Handle, Scope, TransformFunc, generate_name, Context, has_node


# _AUG_OP_MAP = {
#     ast.Add: "+",
#     ast.Sub: "-",
#     ast.Mult: "*",
#     ast.MatMult: "@",
#     ast.Div: "/",
#     ast.Mod: "%",
#     ast.Pow: "**",
#     ast.LShift: "<<",
#     ast.RShift: ">>",
#     ast.BitOr: "|",
#     ast.BitXor: "^",
#     ast.BitAnd: "&",
#     ast.FloorDiv: "//",
# }

def choose_assign(node: ast.Name | ast.Attribute | ast.Subscript, value: str, transform: TransformFunc, ctx: Context):
    # i hope that's all of them
    if isinstance(node, ast.Name):
        # direct bind
        print(ctx.assignment_temp_vars, "assignment temp vars")
        # real_name = ctx.assignment_temp_vars.get(node, node.id)
        real_name = node.id
        # real_name = ctx.assignment_temp_vars[node]
        print(real_name)

        if real_name in ctx.global_vars:
            return f"globals().update({{{real_name!r}: {value}}})"
        elif real_name in ctx.nonlocal_vars:
            # TODO make readable
            ctypes_var = generate_name(prefix="__ctypes_")
            pycellset_var = generate_name(prefix="__pycellset_")
            pyobject_var = generate_name(prefix="__pyobject_")
            item_var = generate_name(prefix="__item_")
            return f"(lambda {ctypes_var}, {item_var}: setattr({pycellset_var} := {ctypes_var}.pythonapi.PyCell_Set, 'argtypes', [{pyobject_var} := {ctypes_var}.py_object, {pyobject_var}]) or {pycellset_var}({item_var}, {pyobject_var}({value})))(__import__('ctypes'), {ctx.current_function.name}.__closure__[{ctx.current_function.name}.__code__.co_freevars.index({real_name!r})])"

        if ctx.scope == Scope.CLASS:
            return f"{ctx.class_dict_var}.update({{{real_name!r}: {value}}}) or ({real_name} := {value})"
        else:
            return f"{real_name} := {value}"
    elif isinstance(node, ast.Attribute):
        return f"setattr({transform(node.value)}, {node.attr!r}, {value})"
    elif isinstance(node, ast.Subscript):
        return f"{transform(node.value)}.__setitem__({transform(node.slice)}, {value})"
    else:
        raise SyntaxError("????")

@Handle(ast.Assign)
def handle_assign(node: ast.Assign, transform: TransformFunc, ctx: Context):
    ctx.assignment_temp_vars.clear()  # clear temp vars for this assignment
    value = transform(node.value)
    print(node.targets)
    if all(not isinstance(i, (ast.Tuple, ast.List)) for i in node.targets):
        # no unpacking
        if len(node.targets) == 1:
            # target = transform(node.targets[0])
            return "(" + choose_assign(node.targets[0], value, transform, ctx) + ")"

        tmp_val = generate_name(prefix="__assign_tmp_")
        return f"[({tmp_val} := {value}), {', '.join(choose_assign(t, tmp_val, transform, ctx) for t in node.targets)}]"
    else:
        # god damnit
        out = []
        has_walrus = has_node(node, ast.NamedExpr)
        if has_walrus or len(node.targets) > 1:
            tmp_val = generate_name(prefix="__assign_tmp_")
            out.append(f"({tmp_val} := {value})")
        else:
            tmp_val = value

        for target in node.targets:
            unpacked = transform(target) # TODO strip parentheses from transform(target) if it added any, to avoid double parentheses in the generated code
            names = ", ".join(choose_assign(var, mangled, transform, ctx) for var, mangled in ctx.assignment_temp_vars.items())

            out.append(f"[[{names}] for {unpacked} in {tmp_val}]")

        return f"[{', '.join(out)}]"

@Handle(ast.AugAssign)
def handle_aug_assign(node: ast.AugAssign, transform: TransformFunc, ctx: Context):
    # name = name op value
    left = deepcopy(node.target)
    left.ctx = ast.Load()  # treat target as load to get the current value
    assignment = ast.Assign(
        targets=[node.target],
        value=ast.BinOp(
            left=left,
            op=node.op,
            right=node.value
        )
    )
    return transform(assignment)

@Handle(ast.AnnAssign)
def handle_ann_assign(node: ast.AnnAssign, transform: TransformFunc, ctx: Context):
    if node.simple and isinstance(node.target, ast.Name):
        # simple case, just a variable annotation (with optional value)
        target = node.target
        annotation = transform(node.annotation)
        if node.value:
            value = transform(node.value)
            if ctx.scope == Scope.MODULE:
                # can save to __annotations__
                return f"[{choose_assign(target, value, transform, ctx)}, __annotations__.update({{{target.id!r}: {annotation}}})]"
            elif ctx.scope == Scope.CLASS:
                # can save to __annotations__ of the class dict
                return f"[{choose_assign(target, value, transform, ctx)}, {ctx.class_dict_var}.setdefault('__annotations__', {{}}).update({{{target.id!r}: {annotation}}})]"
            # return f"({target.id} := {value})  # type: {annotation}"
            else:
                # can't save to __annotations__, just do the assignment and ignore the annotation (PEP 526 allows this)
                return "(" + choose_assign(target, value, transform, ctx) + ")"
        else:
            if ctx.scope == Scope.MODULE:
                return f"__annotations__.update({{{target.id!r}: {annotation}}})"
            elif ctx.scope == Scope.CLASS:
                return f"{ctx.class_dict_var}.setdefault('__annotations__', {{}}).update({{{target.id!r}: {annotation}}})"
            # return f"{target.id}  # type: {annotation}"
    else:
        # no need to save to __annotations__, just do the assignment and ignore the annotation (PEP 526 allows this)
        if node.value:
            assignment = ast.Assign(
                targets=[node.target],
                value=node.value
            )
            return transform(assignment)

    raise SyntaxError("Unrealistic annotated assignment")


@Handle(ast.NamedExpr)
def handle_named_expr(node: ast.NamedExpr, transform: TransformFunc, ctx: Context):
    value = transform(node.value)
    target = transform(node.target)
    return f"({target} := {value})"



@Handle(ast.Delete)
def handle_delete(node: ast.Delete, transform: TransformFunc, ctx: Context):
    # TODO
    items = ", ".join(
        f"({transform(i)})"
        for i in node.targets
    )
    return f"exec({repr(f'del {items}')}, globals(), locals())"

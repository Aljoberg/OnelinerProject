import ast, builtins, string, itertools, keyword

sln = ", "

# TODO make error messages (in the future) also have line num and col


class LambdaManager:

    def __init__(self):
        self.lambdas = {}

    def create_lambda(
        self,
        func_name,
        lambda_exp,
        variables_dict_name,
        scopes,
        current_function,
        prepend,
        async_adder
    ):
        self.lambdas[func_name] = (
            func_name  # resolve_variable(func_name, scopes, current_function)
        ) # FIXME lmao what is this code
        if async_adder:
            return prepend(f"(({func_name} := {lambda_exp}), {async_adder})")
        else:
            return prepend(f"({func_name} := {lambda_exp})")
        # return f"({variables_dict_name}.update({{{repr(func_name)}: {lambda_exp}}}))"

    def get_lambda(self, func_name):
        print("Lambdada")
        print(self.lambdas)
        # input()
        return self.lambdas.get(func_name)


lambda_manager = LambdaManager()

global_vars = {}
# assigned_vars = []
nonlocal_vars = {}
# nonlocal_helpers = {}

forbidden_names = set[str]()

check = lambda first, lookup: any(
    (
        check(i.elts, lookup) in lookup
        if isinstance(i, ast.List | ast.Tuple)
        else (i.id in lookup if isinstance(i, ast.Name) else False)
    )
    for i in first
)


class LambdaWrapper:

    def __init__(self, func, args, body):
        self.func = func
        self.args = args
        self.body = body

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __repr__(self):
        return f"lambda {', '.join(self.args)}: {self.body}"


def generate_variable_name():
    possible_chars = string.ascii_letters
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
    return name


# assigned_vars = {"__global": []}


def parse_assign(node: ast.Assign, tsn, current_loop_and_function):

    targets = node.targets
    value = node.value

    # Function to recursively parse targets and build the assignment expressions
    def parse_target(target, expr):
        if isinstance(target, ast.Name):
            # Simple variable assignment
            if target.id in global_vars.get(current_loop_and_function[0]["name"], []):
                return f"globals().update({{{target.id!r}: {expr}}})"
            return f"{target.id} := {expr}"
        elif isinstance(target, ast.Starred):
            # Handling Starred variable (e.g., *rest)
            return f"{target.value.id} := {expr}"  # TODO: target.value is not neccessarily an ast.Name
        elif isinstance(target, (ast.Tuple, ast.List)):
            # Multiple items (tuple or list unpacking)
            elements = []
            for i, t in enumerate(target.elts):
                if isinstance(t, ast.Starred):
                    # Specially handle starred in unpacking
                    elements.append(parse_target(t, f"list({expr}[{i}:])"))
                else:
                    elements.append(parse_target(t, f"{expr}[{i}]"))
            return ", ".join(elements)
        else:
            raise TypeError("Unsupported target type for assignment.")

    # Use the first target for the assignment expression in the generator
    # first_target_expression = parse_target(targets[0], "i")
    temp_var = generate_variable_name()
    target_exprs = [parse_target(t, temp_var) for t in targets]
    # Create a generator expression using the first target as the temporary variable

    gen_expr_code = f"[{temp_var} := {tsn(value)}, {', '.join(target_exprs)}]"

    return gen_expr_code


def import_node_to_code(node: ast.Import):  # TODO: make temp variable
    lines = []
    for alias in node.names:
        if alias.asname:
            lines.append(f"({alias.asname} := __import__({alias.name!r}))")
        else:
            mod_name = alias.name.split(".")[0]
            lines.append(f"({mod_name} := __import__({alias.name!r}))")
    return lines


def import_from_node_to_code(node: ast.ImportFrom):
    lines = []
    module = node.module or ""
    level = node.level
    # import_cached_varname = None if len(node.names) == 1 else generate_variable_name()
    import_cached_varname = (
        generate_variable_name()
    )  # TODO not needed if only one module
    import_string = f"{f'({import_cached_varname} := ' if import_cached_varname else ''}__import__({module!r}, globals(), locals(), [{', '.join(repr(i.asname if i.asname else i.name) for i in node.names)}], {level}){')' if import_cached_varname else ''}"
    import_var = import_cached_varname or import_string
    for alias in node.names:
        if alias.name == "*":
            k = generate_variable_name()
            # lines.append(
            #     f"exec('from {module} import *')"
            # )  # Using exec for wildcard import
            # fucking ni treba tega jebenega sranja
            # still cool tho
            lines.append(
                f"globals().update({{{k}: getattr({import_cached_varname}, {k}) for {k} in getattr({import_cached_varname}, '__all__', 0) or (i for i in dir({import_cached_varname}) if not i.startswith('__'))}})"
            )
            # lines.append(f"({frame_var} := __import__('inspect').stack()[0][0], {frame_var}.f_locals.update({{{k}: getattr({import_cached_varname}, {k}) for {k} in getattr({import_cached_varname}, '__all__', 0) or (i for i in dir({import_cached_varname}) if not i.startswith('__'))}}), ({ctypes_var} := __import__('ctypes')).pythonapi.PyFrame_LocalsToFast({ctypes_var}.py_object({frame_var}), {ctypes_var}.c_int(0)))")
            # if current_function is not None: # TODO move to function def
            #     code_var = generate_variable_name()
            #     lines.append(f"setattr({current_function}, '__code__', ({code_var} := {current_function}.__code__).replace(co_flags={code_var}.co_flags & 0xFFFE))")
            # TODO PyFrame_LocalsToFast for inspect.stack()[0][0] & remove CO_OPTIMIZED if in a scope
            # if in a global namespace, frame.f_locals is writeable & no need to call PyFrame_LocalsToFast (afaik, not sure for python 3.13)
        elif alias.asname:
            lines.append(f"({alias.asname} := {import_var}.{alias.name})")
        else:
            lines.append(f"({alias.name} := {import_var}.{alias.name})")
    return f"{f'({import_string}, ' if import_cached_varname else ''}{', '.join(lines)}{')' if import_cached_varname else ''}"


def transform_assignment(
    node,
    current_function,
    variables_dict_name,
    scopes,
    arg_def=False,
    optvars=None,  # , assign_surely=False
):
    # return f"({node.targets[0].id} := {sans.transform_node(node.value, current_function, variables_dict_name, scopes)})"
    # if type(node) == str: return f"({node} := {node})" # TODO: THIS IS BAD
    if arg_def:
        # return f"(lambda {optvars or ''}: {variables_dict_name}.update({{{repr(node)}: {node}}}) or {variables_dict_name}.get({repr(node)}))({optvars or ''})"
        raise NotImplementedError
    # for i in node.targets: assigned_vars[current_function[0] or "__global"].append(i.id if isinstance(i, ast.Name) else i.value.id)
    value = sans.transform_node(node.value, current_function, variables_dict_name)

    # for i in node.targets: add_targets(i)
    if isinstance(node, ast.AnnAssign):
        # TODO: implement __annotations__
        target = node.target
        value = node.value

        value_transformed = sans.transform_node(
            value, current_function, variables_dict_name
        )
        if isinstance(target, ast.Name):
            target = target.id
            return f"({target} := {value_transformed})"
        elif isinstance(target, ast.Attribute):
            target = sans.transform_node(value, current_function, variables_dict_name)

            return f"setattr({target.value.id}, {target.attr!r}, {value_transformed})"
        else:
            raise NotImplementedError(
                f"Annotated assignment to {type(target)} not implemented"
            )

    # elif all(isinstance(stmt, ast.Name) for stmt in node.targets):
    else:
        tsn = lambda itemm: sans.transform_node(
            itemm, current_function, variables_dict_name
        )
        m = node.targets.copy()
        m.append(node.value)

        # TODO: ugotovitve vrta
        # daj v lambdo za temporary variable, updataj `locals()` (kot argument lambdi recimo)
        # avoidaj lambdo, ce je vse ast.Constant v node.value alpa ast.Name, ampak potem ne smejo biti recimo `a, b = b, a`. tisto gre v lambdo.

        return parse_assign(node, tsn, current_function)


class sans:
    # func_dict = None
    pending_assignments = []
    imports_list = []

    @staticmethod
    def transform_node(
        node: ast.AST,
        current_loop_and_function=None,
        varname="__variables",
        scopes=[],
        exc_name=None,
        loop_vars=set(),
    ) -> str:
        if not current_loop_and_function:
            current_loop_and_function = [
                {"name": None, "has_return": False},
                None,
                None,
            ]

        # if not scopes:
        #     scopes = [varname]
        def prepend(contents: str):
            valooe = f"{(current_loop_and_function[0] or {}).get('return_hit_var')} or "  # <3.12 moment
            # valooe_loop = f"not {current_loop_and_function[1]} and not {current_loop_and_function[2]} and "
            valooe_loop = f"any(({current_loop_and_function[1]}, {current_loop_and_function[2]})) or "
            # input()
            return f'({valooe if current_loop_and_function[0]["has_return"] else ""}{valooe_loop if current_loop_and_function[1] else ""}{contents})'

        if isinstance(node, ast.Expr):
            return prepend(
                f'{sans.transform_node(node.value, current_loop_and_function, f"{varname}", scopes, exc_name, loop_vars)}'
            )
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            global_vars[node.name] = []
            nonlocal_vars[node.name] = []
            # assigned_vars[node.name] = []
            # scopes.append(f"__variables_{node.name}")
            empty_str = ""  # i hate f strings
            equal = "="
            pos_args = [arg.arg for arg in node.args.args]
            vararg = node.args.vararg.arg if node.args.vararg else None
            kwarg = node.args.kwarg.arg if node.args.kwarg else None
            print("posargs")
            print(pos_args)
            vkwargs = ([f"*{vararg}"] if vararg else []) + (
                [f"**{kwarg}"] if kwarg else []
            )
            has_return = any(
                [
                    isinstance(stmt, ast.Return)
                    for stmt in ast.walk(node)
                    # if isinstance(stmt, ast.Expr)
                ]
            )
            """nested_nonlocal = [
                x
                for xs in filter(
                    None,
                    (
                        isinstance(n, ast.FunctionDef)
                        and (not nonlocal_vars.get(n.name))
                        and print(list(ast.walk(n))) or True
                        and next(
                            filter(
                                None,
                                (
                                    isinstance(m, ast.Nonlocal) and m.names
                                    for m in ast.walk(n)
                                ),
                            ),
                            None,
                        )
                        for j in node.body
                        for n in ast.walk(j)
                    ),
                )
                for x in xs
            ]"""
            """nested_nonlocal = list(
                set(
                    sum(
                        [
                            [name for name in nd.names]
                            for sub in node.body
                            if isinstance(sub, ast.FunctionDef)
                            for nd in ast.walk(sub)
                            if isinstance(nd, ast.Nonlocal)
                        ],
                        [],
                    )
                )
            )

            l_n_h = {}
            for i in nested_nonlocal:
                if nonlocal_helpers.get(i):
                    continue
                v = generate_variable_name()
                nonlocal_helpers[i] = v
                l_n_h[i] = v
            print(nonlocal_helpers, "nonlhelpers")
            print(nested_nonlocal, "nnl")
            print(has_return, "has return")"""
            all_args = pos_args + vkwargs
            return_store_var = generate_variable_name()
            return_hit_var = generate_variable_name()
            body_statements = [
                sans.transform_node(
                    stmt,
                    [
                        {
                            "name": node.name,
                            "has_return": has_return,
                            "return_hit_var": return_hit_var,
                            "return_store_var": return_store_var,
                        },
                        *current_loop_and_function[1:],
                    ],
                    f"__variables_{node.name}",
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for stmt in node.body
            ]

            print(body_statements)
            print(all_args)
            """print(l_n_h, "lnh")
            for n, v in l_n_h.items():
                body_statements = [f"{v} := lambda: {n}"] + body_statements"""
            args = ", ".join(all_args)
            print(body_statements)
            body = ", ".join(body_statements)
            init_args = ", ".join(
                list(
                    f"{arg[0].arg}{f'{equal + sans.transform_node(arg[1], current_loop_and_function, varname, scopes, exc_name, loop_vars) if arg[1] else empty_str}'}"
                    for arg in zip(
                        node.args.args,
                        [
                            None
                            for _ in range(
                                len(node.args.args) - len(node.args.defaults)
                            )
                        ]
                        + node.args.defaults,
                    )
                )
                + vkwargs
            )

            # TODO clean all of this fucking weird code up
            is_async = isinstance(node, ast.AsyncFunctionDef)
            toggle_async = None
            if is_async:
                code_var = generate_variable_name()
                toggle_async = f"setattr({node.name}, '__code__', ({code_var} := {node.name}.__code__).replace(co_flags={code_var}.co_flags & ~32 | 128))"
                # FIXME move below the declaration, or else it won't be declared yet

            func_expression = f"lambda{(' ' + init_args) if init_args else ''}: {f'({return_store_var} := [None]) and ({return_hit_var} := False) or ' if has_return else ''}[{body}{f', {return_store_var}[0]' if has_return else ', None'}][-1]"
            for i in node.decorator_list:
                func_expression = (
                    f"({sans.transform_node(i, current_loop_and_function, varname, scopes, exc_name, loop_vars)})("
                    + func_expression
                    + ")"
                    # + f" and {node.name}.__code__"  # TODO <- idk what i meant here but look it up
                )

            # scopes.pop()

            if isinstance(node.parent, ast.ClassDef):
                return func_expression
            return lambda_manager.create_lambda(
                node.name,
                func_expression,
                varname,
                scopes,
                current_loop_and_function[0]["name"],
                prepend,
                toggle_async
            )

        elif isinstance(node, ast.Name):
            if hasattr(builtins, node.id) or isinstance(node.ctx, ast.Store):
                return node.id
            elif lambda_manager.get_lambda(node.id):
                return lambda_manager.get_lambda(node.id)
            print(node.id)
            return node.id
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func_name = lambda_manager.get_lambda(node.func.id) or node.func.id
            args = [
                sans.transform_node(
                    arg, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for arg in node.args
            ]
            kwargs = [
                f"{kw.arg}={sans.transform_node(kw.value, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                for kw in node.keywords
            ]

            all_args = args + kwargs
            if hasattr(builtins, func_name) or lambda_manager.get_lambda(node.func.id):
                return f"{func_name}({sln.join(all_args)})"
            return prepend(f"{func_name}({sln.join(all_args)})")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            func_name = sans.transform_node(
                node.func,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            args = [
                sans.transform_node(
                    arg, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for arg in node.args
            ]
            kwargs = [
                f"{kw.arg}={sans.transform_node(kw.value, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                for kw in node.keywords
            ]
            all_args = args + kwargs

            return f"{func_name}({sln.join(all_args)})"
        elif isinstance(node, ast.Call) and isinstance(
            node.func, ast.Lambda | ast.Call
        ):
            func_name = sans.transform_node(
                node.func,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            args = [
                sans.transform_node(
                    arg, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for arg in node.args
            ]
            kwargs = [
                f"{kw.arg}={sans.transform_node(kw.value, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                for kw in node.keywords
            ]
            all_args = args + kwargs
            return f"{func_name}({sln.join(all_args)})"
        elif isinstance(node, ast.Attribute):
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            return f"{value}.{node.attr}"
        elif isinstance(node, ast.If):
            test = sans.transform_node(
                node.test,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            body_statements = [
                sans.transform_node(
                    stmt,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for stmt in node.body
            ]
            orelse_statements = [
                sans.transform_node(
                    stmt,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for stmt in node.orelse
                if stmt
            ]

            body = ", ".join(body_statements)
            orelse = ", ".join(orelse_statements)
            return prepend(f"(({body}) if ({test}) else ({orelse or None}))")

        elif isinstance(node, ast.For | ast.AsyncFor):
            break_hit_var = generate_variable_name()
            continue_hit_var = generate_variable_name()
            current_loop_and_function = [
                current_loop_and_function[0],
                (
                    break_hit_var
                    if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node))
                    else None
                ),
                (
                    continue_hit_var
                    if any(isinstance(stmt, ast.Continue) for stmt in ast.walk(node))
                    else None
                ),
            ]
            """if isinstance(node.target, ast.Name):
                loop_vars.add(node.target.id)
            elif isinstance(node.target, ast.Tuple):
                for i in node.target.elts:
                    loop_vars.add(i.id)
            else:
                raise Exception(f"wtf its type is {type(node.target)}")"""
            target = sans.transform_node(
                node.target,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            iter_ = sans.transform_node(
                node.iter,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )

            body_statements = [
                sans.transform_node(
                    stmt,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for stmt in node.body
            ]

            combined_body = body_statements
            combined_body = list(f"({i})" for i in combined_body)

            """if isinstance(node.target, ast.Name):
                loop_vars.remove(node.target.id)
            elif isinstance(node.target, ast.Tuple):
                for i in node.target.elts:
                    loop_vars.remove(i.id)"""
            return prepend(
                f"[{f'({break_hit_var} := False), ' if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node)) else ''}[({f'({continue_hit_var} := False), ' if any(isinstance(stmt, ast.Continue) for stmt in ast.walk(node)) else ''}{', '.join(combined_body)}) {'async ' if isinstance(node, ast.AsyncFor) else ''}for {target} in {iter_}]]"
            )

        elif isinstance(node, ast.Assign):  # TODO: implement in ast.AugAssign
            print(current_loop_and_function)
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            # set_item_lambda = "(lambda d, k, v: d.__setitem__(k, v))"
            set_item = "{}.__setitem__({}, {})"
            if any(
                isinstance(i, ast.Subscript) for i in node.targets
            ):  # FIXME: implement recursive searching, for example: `a, (b.c) = 1, 2` and same but b["c"]
                assignments = [
                    set_item.format(
                        sans.transform_node(
                            t.value,
                            current_loop_and_function,
                            varname,
                            scopes,
                            exc_name,
                            loop_vars,
                        ),
                        sans.transform_node(
                            t.slice,
                            current_loop_and_function,
                            varname,
                            scopes,
                            exc_name,
                            loop_vars,
                        ),
                        value,
                    )
                    for t in node.targets
                    if isinstance(t, ast.Subscript)
                ]
                return prepend(f"{' and '.join(assignments)}")
            if any(isinstance(i, ast.Attribute) for i in node.targets):
                assignments = [
                    f"setattr({sans.transform_node(t.value, current_loop_and_function, varname, scopes, exc_name, loop_vars)}, {t.attr!r}, {value})"
                    for t in node.targets
                    if isinstance(t, ast.Attribute)
                ]
                return prepend(f"{' and '.join(assignments)}")

            if check(
                node.targets,
                nonlocal_vars.get(current_loop_and_function[0]["name"], []),
            ):  # TODO: implement in transform_assignment, and don't use node.targets[0].id but embed in transform_assignment
                ctypes_var = generate_variable_name()
                item_var = generate_variable_name()
                pycellset_var = generate_variable_name()
                pyobject_var = generate_variable_name()
                return prepend(
                    f"(lambda {ctypes_var}, {item_var}: setattr({pycellset_var} := {ctypes_var}.pythonapi.PyCell_Set, 'argtypes', [{pyobject_var} := {ctypes_var}.py_object, {pyobject_var}]) or {pycellset_var}({item_var}, {pyobject_var}({value})))(__import__('ctypes'), {current_loop_and_function[0]['name']}.__closure__[{current_loop_and_function[0]['name']}.__code__.co_freevars.index({node.targets[0].id!r})])"
                )
            #            if not check(node.targets, assigned_vars):

            """def append(iterable, first):
                    if isinstance(iterable, ast.Name):
                        return iterable
                    elif isinstance(iterable, ast.List | ast.Tuple) and not first:
                        return iterable.elts
                    for i in iterable:
                        assigned_vars.append(append(i, False))

                append(node.targets, True)"""
            return prepend(
                transform_assignment(node, current_loop_and_function, varname, scopes)
            )
        #           elif len(node.targets) == 1:
        #                return prepend + transform_assignment(
        #                   node, current_loop_and_function, varname, scopes
        #               )
        # return f"{valooe if current_loop_and_function[0] else ''}{transform_assignment(node, current_loop_and_function, varname, scopes)}"

        elif isinstance(node, ast.BinOp):
            left = sans.transform_node(
                node.left,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            op = sans.transform_node(
                node.op, current_loop_and_function, varname, scopes, exc_name, loop_vars
            )
            right = sans.transform_node(
                node.right,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            return f"({left} {op} {right})"
        elif isinstance(node, ast.Add):
            return "+"
        elif isinstance(node, ast.Sub):
            return "-"
        elif isinstance(node, ast.Pow):
            return "**"
        elif isinstance(node, ast.Compare):
            left = sans.transform_node(
                node.left,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            ops = [
                sans.transform_node(
                    op, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for op in node.ops
            ]
            comparators = [
                sans.transform_node(
                    comparator,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for comparator in node.comparators
            ]
            comparisons = " ".join(
                f"{op} {comparator}" for op, comparator in zip(ops, comparators)
            )
            return f"({left} {comparisons})"
        elif isinstance(node, ast.Eq):
            return "=="
        elif isinstance(node, ast.NotEq):
            return "!="
        elif isinstance(node, ast.Lt):
            return "<"
        elif isinstance(node, ast.LtE):
            return "<="
        elif isinstance(node, ast.Gt):
            return ">"
        elif isinstance(node, ast.GtE):
            return ">="
        elif isinstance(node, ast.Div):
            return "/"
        elif isinstance(node, ast.Constant):
            if node.value is None:
                return "None"
            if node.value == ...:
                return "..."
            if isinstance(node.value, (str, int, float)):
                return repr(node.value)
            else:
                raise NotImplementedError(
                    f"Constant type {type(node.value)} not implemented."
                )
        elif isinstance(node, ast.Return):
            if current_loop_and_function[0]:
                if node.value:
                    value = sans.transform_node(
                        node.value,
                        current_loop_and_function,
                        varname,
                        scopes,
                        exc_name,
                        loop_vars,
                    )
                    # return f"{varname}.update({ {'__return_value': value} }) or None"
                    # update_lambda = "(lambda d, k, v: (d.__setitem__(k, v), v))"
                    return prepend(
                        f"({current_loop_and_function[0]['return_store_var']}.__setitem__(0, {value}) or ({current_loop_and_function[0]['return_hit_var']} := True))"
                    )
                else:
                    return prepend(
                        f"({current_loop_and_function[0]['return_hit_var']} := True)"
                    )
            else:
                raise SyntaxError("return outside function wtf")
        elif isinstance(node, ast.List):
            elements = ", ".join(
                sans.transform_node(
                    e, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for e in node.elts
            )
            return f"[{elements}]"

        elif isinstance(node, ast.Tuple):
            elements = ", ".join(
                sans.transform_node(
                    e, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for e in node.elts
            )
            return (
                f"{elements},"
                if isinstance(node.parent, ast.Subscript)
                else f"({elements},)"
            )

        elif isinstance(node, ast.Dict):
            keys = [
                sans.transform_node(
                    k, current_loop_and_function, varname, exc_name, loop_vars
                )
                for k in node.keys
            ]
            values = [
                sans.transform_node(
                    v, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for v in node.values
            ]
            pairs = ", ".join(f"{k}: {v}" for k, v in zip(keys, values))
            return f"{{{pairs}}}"
        elif isinstance(node, ast.GeneratorExp):
            elt = sans.transform_node(
                node.elt,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            generators = [
                sans.transform_node(
                    gen, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for gen in node.generators
            ]
            gen_expression = f"({elt} for {', '.join(generators)})"
            return gen_expression
        elif isinstance(node, ast.comprehension):
            target = sans.transform_node(
                node.target,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            iter_ = sans.transform_node(
                node.iter,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            ifs = [
                sans.transform_node(
                    if_expr,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for if_expr in node.ifs
            ]
            comprehension = f"{target} in {iter_}"
            # print(ifs)
            if ifs:
                comprehension += f" if {' and '.join(ifs)}"
            # print(comprehension)
            # input()
            return comprehension
        elif isinstance(node, ast.Mult):
            return "*"
        elif isinstance(node, ast.ListComp):
            elt = sans.transform_node(
                node.elt,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            generators = [
                sans.transform_node(
                    gen, current_loop_and_function, varname, scopes, exc_name, loop_vars
                )
                for gen in node.generators
            ]
            comprehension = f"[{elt} for {', '.join(generators)}]"
            return comprehension
        elif isinstance(node, ast.Mod):
            return "%"
        elif isinstance(node, ast.FloorDiv):
            return "//"
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value = node.value

            if isinstance(target, ast.Name):
                target_repr = repr(target.id)
            elif isinstance(target, ast.Attribute):
                target_repr = f"{sans.transform_node(target.value, current_loop_and_function, varname)}.{target.attr}"
            else:
                raise NotImplementedError(
                    f"Annotated assignment to {type(target)} not implemented"
                )

            value_transformed = sans.transform_node(
                value, current_loop_and_function, varname
            )
            # annotation_transformed = transform_node(annotation, current_loop_and_function, varname)
            # return f"(lambda: {varname}.update({{{target_repr}: {value_transformed}}}) or None)()"
            return prepend(f"({target} := {value})")
        elif isinstance(node, ast.ClassDef):  # TODO: redo the whole thing
            # TODO keywords with types.new_class or sum
            class_name = node.name
            base_classes = [
                sans.transform_node(
                    base,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for base in node.bases
            ]
            class_dict = {}
            annotations_dict = {}
            for stmt in node.body:
                if isinstance(stmt, ast.FunctionDef):
                    # global_vars[node.name] = []
                    # nonlocal_vars[node.name] = []
                    # assigned_vars[node.name] = []
                    class_dict[stmt.name] = sans.transform_node(
                        stmt,
                        current_loop_and_function,
                        varname,
                        scopes,
                        exc_name,
                        loop_vars,
                    )
                elif isinstance(stmt, ast.AnnAssign) and stmt.simple:
                    transformed_assignment = transform_assignment(
                        stmt, None, varname, scopes, False
                    )
                    if isinstance(stmt.target, ast.Name):
                        print(stmt.annotation)
                        annotations_dict[stmt.target.id] = sans.transform_node(
                            stmt.annotation,
                            current_loop_and_function,
                            varname,
                            scopes,
                            exc_name,
                            loop_vars,
                        )
                        class_dict[stmt.target.id] = transformed_assignment
                    elif isinstance(stmt.target, ast.Attribute):
                        pass
                    else:
                        raise NotImplementedError(
                            f"Annotated assignment to {type(stmt.target)} not implemented in class definition"
                        )
            # print(class_dict)
            kv_conv = (
                lambda d: f"{{{', '.join(f'{key!r}: {value}' for key, value in d.items())}}}"
            )
            if annotations_dict:
                class_dict = {
                    "__annotations__": kv_conv(annotations_dict),
                    **class_dict,
                }
            cls = f"(type({class_name!r}, ({', '.join(base_classes)}{',' if len(base_classes) == 1 else ''}), {kv_conv(class_dict)}))"
            for i in node.decorator_list:
                cls = (
                    f"({sans.transform_node(i, current_loop_and_function, varname, scopes, exc_name, loop_vars)})("
                    + cls
                    + ")"
                )
            # return f"({varname}.update({{{repr(class_name)}: {cls}}}))"
            return prepend(f"({class_name} := {cls})")
        elif isinstance(node, ast.Import):
            return prepend(", ".join(import_node_to_code(node)))

        elif isinstance(node, ast.ImportFrom):
            return prepend(import_from_node_to_code(node))

        # return " and ".join(imports)
        elif isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant):
                    parts.append(repr(part.s))
                elif isinstance(part, ast.FormattedValue):
                    expr = sans.transform_node(
                        part.value,
                        current_loop_and_function,
                        varname,
                        scopes,
                        exc_name,
                        loop_vars,
                    )

                    if part.format_spec:
                        format_spec = sans.transform_node(
                            part.format_spec,
                            current_loop_and_function,
                            varname,
                            scopes,
                            exc_name,
                            loop_vars,
                        )
                        parts.append(f"str({expr}).format({format_spec})")
                    else:
                        parts.append(f"str({expr})")
                else:
                    raise TypeError(
                        f"Unsupported type for JoinedStr part: {type(part).__name__}"
                    )
            return " + ".join(parts)

        elif isinstance(node, ast.FormattedValue):
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            if node.format_spec:
                format_spec = sans.transform_node(
                    node.format_spec,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                return f"format({value}, {format_spec})"
            else:
                return f"{value}"

        elif isinstance(node, ast.While):
            break_hit_var = generate_variable_name()
            continue_hit_var = generate_variable_name()
            current_loop_and_function = [
                current_loop_and_function[0],
                (
                    break_hit_var
                    if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node))
                    else None
                ),
                (
                    continue_hit_var
                    if any(isinstance(stmt, ast.Continue) for stmt in ast.walk(node))
                    else None
                ),
            ]
            test = sans.transform_node(
                node.test,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            body_statements = [
                f"({sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)})"
                for stmt in node.body
            ]
            body = (
                "["
                + (
                    f"({continue_hit_var} := False), "
                    if any(isinstance(stmt, ast.Continue) for stmt in ast.walk(node))
                    else ""
                )
                + ", ".join(body_statements)
                + "]"
            )
            underscore_var = generate_variable_name()
            underscore_var_2 = generate_variable_name()
            body_var = generate_variable_name()
            # loop_gen = f"[{f'({break_hit_var} := False), ' if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node)) else ''}list(__import__('itertools').takewhile(lambda {', '.join(dependencies)}: not {break_hit_var} and ({test}), ([({f'({continue_hit_var} := False), ' if any(isinstance(stmt, ast.Continue) for stmt in ast.walk(node)) else ''}{body}), {', '.join(dependencies)}][-1] for {underscore_var} in iter(int, 1))))]"
            loop_gen = f"[{f'({break_hit_var} := False), ' if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node)) else ''}{body_var} := (({body} and {f'not {break_hit_var} and ' if any(isinstance(stmt, ast.Break) for stmt in ast.walk(node)) else ''}{test}) for {underscore_var} in iter(int, 1)), [None for {underscore_var_2} in iter(lambda: next({body_var}), False)]]"
            return prepend(loop_gen)

        # elif isinstance(node, (ast.Try, getattr(ast, "TryStar", None) or ast.Try)): TODO: make trystar
        elif isinstance(node, ast.Try):
            try_body = (
                "["
                + ", ".join(
                    f"{sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                    for stmt in node.body
                )
                + "] for _ in [0]"
            )
            handlers: list[tuple[str | None, str, str]] = (
                [  # exception class, exception variable, handler body
                    (
                        (
                            handler.type
                            and sans.transform_node(
                                handler.type,
                                current_loop_and_function,
                                varname,
                                scopes,
                                exc_name,
                                loop_vars,
                            )
                        ),
                        handler.name or generate_variable_name(),
                        "["
                        + ", ".join(
                            f"{sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                            for stmt in handler.body
                        )
                        + "]",
                    )
                    for handler in node.handlers
                ]
            )

            # Process exception handlers
            # for handler in node.handlers:
            #     exc_type = (
            #         sans.transform_node(
            #             handler.type,
            #             current_loop_and_function,
            #             varname,
            #             scopes,
            #             exc_name,
            #             loop_vars,
            #         )
            #         if handler.type
            #         else ""
            #     )
            #     exc_name = handler.name or ""

            #     handler_body = (
            #         "["
            #         + ", ".join(
            #             f"{sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
            #             for stmt in handler.body
            #         )
            #         + "]"
            #     )

            #     handlers.append(
            #         f'except{"*" if hasattr(ast, "TryStar") and isinstance(node, ast.TryStar) else ""}{f" {exc_type}" if exc_type else ""}{f" as {exc_name}" if exc_name else ""}: {handler_body}'
            #     )

            # Process orelse part
            orelse_body = ""
            if node.orelse:
                orelse_body = (
                    "["
                    + ", ".join(
                        f"{sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                        for stmt in node.orelse
                    )
                    + "]"
                )

            # Process finalbody part
            finalbody = ""
            if node.finalbody:
                finalbody = (
                    "["
                    + ", ".join(
                        f"{sans.transform_node(stmt, current_loop_and_function, varname, scopes, exc_name, loop_vars)}"
                        for stmt in node.finalbody
                    )
                    + "]"
                )

            # name_references = {
            #     *(
            #         i.id
            #         for m in node.body
            #         for i in ast.walk(m)
            #         if isinstance(i, ast.Name)
            #         and isinstance(i.ctx, ast.Load)
            #         and not hasattr(builtins, i.id)
            #     ),
            #     current_loop_and_function[0]["name"],
            # }
            # try_except_func = f"exec({f'try: {try_body}{newline}{handlers_chain}{newline}{orelse_body}{newline}{finalbody}'!r}, globals(), {{{(lambda s: s + ', ' if s else '')(', '.join(f'{i!r}: {i}' for i in name_references))}**locals()}})"

            exc_variable = generate_variable_name()
            try_variable = generate_variable_name()
            else_variable = generate_variable_name()
            finally_variable = generate_variable_name()
            exc_in_exit_variable_used = generate_variable_name()
            exc_in_exit_variable_0 = generate_variable_name()
            exc_in_exit_variable_2 = generate_variable_name()
            self_variable = generate_variable_name()
            exc_1_variable = generate_variable_name()
            orelse_iter_variable = generate_variable_name()
            finally_iter_variable = generate_variable_name()
            handler_global_vars = []

            try_except_func = f"""\
({exc_variable} := [], {try_variable} := ({try_body}), \
({', '.join(f'{(lambda var: handler_global_vars.append(var) or var)(generate_variable_name())} := \
({body} for {exc_var} in {exc_variable})' for _, exc_var, body in handlers)}), \
{orelse_body and f'{else_variable} := ({orelse_body} for {orelse_iter_variable} in [0]), '}\
{finalbody and f'{finally_variable} := ({finalbody} for {finally_iter_variable} in [0]), '}\
type("__TryExcept", (__import__("contextlib").ContextDecorator,), {{\
"__enter__": lambda {self_variable}: {self_variable}, \
"__exit__": lambda {self_variable}, {exc_in_exit_variable_0}, {exc_in_exit_variable_used}, {exc_in_exit_variable_2}: {exc_in_exit_variable_used} and ({exc_variable}.append({exc_1_variable} := {exc_in_exit_variable_used}) \
or ({' '.join(f'''(*{handler_global_vars[i]},){f' if isinstance({exc_1_variable}, {exc_name}) else' if exc_name else ''}''' for i, (exc_name, _, _) in enumerate(handlers))} {'None' if handlers[-1][0] else ''}))\
{finalbody and f' and (*{finally_variable},) '}\
}})()(lambda: (*{try_variable},{orelse_body and f' *{else_variable}'}))()\
)"""

            print(try_except_func)

            return prepend(try_except_func)

        elif isinstance(node, ast.Subscript):
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            slice_ = sans.transform_node(
                node.slice,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            return f"{value}[{slice_}]"

        elif isinstance(node, ast.BoolOp):
            operator = sans.transform_node(
                node.op, current_loop_and_function, varname, scopes, exc_name, loop_vars
            )
            values = [
                f"({sans.transform_node(value, current_loop_and_function, varname, scopes, exc_name, loop_vars)})"
                for value in node.values
            ]
            print(values, operator, f" {operator} ".join(values))
            return f" {operator} ".join(values)
        elif isinstance(node, ast.And):
            return "and"

        elif isinstance(node, ast.Or):
            return "or"
        elif isinstance(node, ast.UnaryOp):
            operator = sans.transform_node(
                node.op, current_loop_and_function, varname, scopes, exc_name, loop_vars
            )
            operand = sans.transform_node(
                node.operand,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            return f"{operator}{operand}"
        elif isinstance(node, ast.USub):
            return "-"

        elif isinstance(node, ast.UAdd):
            return "+"
        elif isinstance(node, ast.Not):
            return "not "
        elif isinstance(node, ast.NotIn):
            return "not in"
        elif isinstance(node, ast.Invert):
            return "~"
        elif isinstance(node, ast.IfExp):
            test = sans.transform_node(
                node.test,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            body = sans.transform_node(
                node.body,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            orelse = sans.transform_node(
                node.orelse,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            # print(orelse)
            # input()
            return f"({body} if {test} else {orelse})"
        elif isinstance(node, ast.In):
            return "in"
        elif isinstance(node, ast.Lambda):
            args = [arg.arg for arg in node.args.args]
            body = sans.transform_node(
                node.body,
                current_loop_and_function,
                varname,
                scopes + [set(args)],
                exc_name,
                loop_vars,
            )
            return f"(lambda {', '.join(args)}: {body})"
        elif isinstance(node, ast.Slice):
            start = (
                sans.transform_node(
                    node.lower,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                if node.lower
                else ""
            )
            stop = (
                sans.transform_node(
                    node.upper,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                if node.upper
                else ""
            )
            step = (
                sans.transform_node(
                    node.step,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                if node.step
                else ""
            )
            if isinstance(node.parent, ast.Subscript) and isinstance(
                node.parent.ctx, ast.Store
            ):
                start = int(start) if len(start) > 0 else None
                stop = int(stop) if len(stop) > 0 else None
                step = int(step) if len(step) > 0 else None
                return str(
                    slice(start, stop, step)
                )  # TODO move to ast.Assign, shorten if no step (`slice(x, y)` stringifies into "slice(x, y, None)")
            if step:
                return f"{start}:{stop}:{step}"
            else:
                return f"{start}:{stop}"
        elif isinstance(node, ast.Pass):
            return "None"
        elif isinstance(node, ast.Break):
            return f"({current_loop_and_function[1]} := True)"
        elif isinstance(node, ast.Continue):
            return f"({current_loop_and_function[2]} := True)"
        elif isinstance(node, ast.Raise):
            TEMP_NAME = generate_variable_name()
            return prepend(
                f"(_ for _ in ()).throw((lambda {TEMP_NAME}: setattr({TEMP_NAME}, '__cause__', {sans.transform_node(node.cause, current_loop_and_function, varname, scopes, exc_name, loop_vars)}{'()' if isinstance(node.cause, ast.Name) else ''}) or {TEMP_NAME})({sans.transform_node(node.exc, current_loop_and_function, varname, scopes, exc_name, loop_vars)}{'()' if isinstance(node.exc, ast.Name) else ''}))"
            )
        elif isinstance(node, ast.Match):
            subject = sans.transform_node(
                node.subject,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )

            def transform_pattern(pattern, is_nested=False):
                if isinstance(pattern, ast.MatchValue):
                    comparison_value = sans.transform_node(
                        pattern.value,
                        current_loop_and_function,
                        varname,
                        scopes,
                        exc_name,
                        loop_vars,
                    )
                    return (
                        comparison_value
                        if is_nested
                        else f"{subject} == {comparison_value}"
                    )
                elif isinstance(pattern, ast.MatchSingleton):
                    comparison_value = repr(pattern.value)
                    return (
                        comparison_value
                        if is_nested
                        else f"{subject} is {comparison_value}"
                    )
                elif isinstance(pattern, ast.MatchSequence):

                    sequence_conditions = []
                    star = False
                    for i, el in enumerate(pattern.patterns):
                        if isinstance(el, ast.MatchAs) and el.pattern is None:
                            name = el.name or "_"
                            sequence_conditions.append(
                                # f"({varname}.update({{{name!r}: {subject}[{i}]}}) or True)"
                                f"[({name} := {subject}[{i}])] or True"
                            )
                        elif isinstance(el, ast.MatchAs):
                            name = el.name or "_"
                            as_condition = transform_pattern(el.pattern, is_nested)
                            sequence_conditions.append(
                                # f"({varname}.update({{{name!r}: {subject}[{i}]}}) or {as_condition})"
                                f"[({name} := {subject}[{i}]), {as_condition}][-1]"
                            )
                        elif isinstance(el, ast.MatchOr):
                            or_conditions = [
                                f"{subject}[{i}] == {transform_pattern(p, True)}"
                                for p in el.patterns
                            ]
                            sequence_conditions.append(
                                f"({' or '.join(or_conditions)})"
                            )
                        elif isinstance(el, ast.MatchStar):
                            star = True
                            break
                        else:
                            seq_pattern = transform_pattern(el, True)
                            sequence_conditions.append(
                                f"{subject}[{i}] == {seq_pattern}"
                            )
                    length_check = f"(len({subject}) {'>=' if star else '=='} {len(pattern.patterns)})"
                    combined_conditions = " and ".join(sequence_conditions)
                    return f"({length_check} and ({combined_conditions}))"
                elif isinstance(pattern, ast.MatchClass):
                    cls_name = pattern.cls.id
                    attribute_conditions = []
                    keyword_patterns = [
                        f"{subject}.{kwd_attr} == {transform_pattern(kwd_pattern, True)}"
                        for kwd_attr, kwd_pattern in zip(
                            pattern.kwd_attrs, pattern.kwd_patterns
                        )
                    ]
                    for i, attr_pattern in enumerate(pattern.patterns):
                        if isinstance(attr_pattern, ast.MatchAs):
                            name = attr_pattern.name or "_"
                            if attr_pattern.pattern:
                                nested_pattern = transform_pattern(
                                    attr_pattern.pattern, True
                                )
                                attribute_conditions.append(
                                    f"({nested_pattern} and ({varname}.update({{{name!r}: getattr({subject}, {attr_pattern.name!r})}}) or True))"
                                )
                            else:
                                # Just variable binding without a nested pattern
                                attribute_conditions.append(
                                    f"({varname}.update({{{name!r}: getattr({subject}, {attr_pattern.name!r})}}) or True)"
                                )
                        elif isinstance(attr_pattern, ast.MatchValue):
                            # Example for MatchValue, similar approach for other types
                            comparison_value = transform_pattern(
                                attr_pattern.value, True
                            )
                            attribute_conditions.append(
                                f"({comparison_value} == [attr_val for attr_name, attr_val in __import__('inspect').getmembers({subject}, lambda a: not (__import__('inspect').isroutine(a) or __import__('inspect').isbuiltin(a))) if not (attr_name.startswith('__') and attr_name.endswith('__')) and not hasattr(object, attr_name)][{i}])"
                            )

                        else:
                            raise NotImplementedError(
                                f"Attribute pattern type {type(attr_pattern)} not implemented in MatchClass"
                            )

                    instance_check = f"isinstance({subject}, {cls_name})"
                    attribute_conditions.append("True")
                    combined_conditions = " and ".join(
                        attribute_conditions + keyword_patterns
                    )
                    return f"{instance_check} and ({combined_conditions})"

                elif isinstance(pattern, ast.MatchMapping):
                    compare_conditions = []
                    for key, value_pattern in zip(pattern.keys, pattern.patterns):
                        transformed_key = transform_pattern(
                            key, True
                        )  # Transform the key for comparison

                        if isinstance(value_pattern, ast.MatchAs):
                            value_name = value_pattern.name or "_"
                            value_from_subject = f"{subject}.get({transformed_key})"
                            if value_pattern.pattern:
                                if isinstance(value_pattern.pattern, ast.MatchClass):
                                    # Handling MatchClass in MatchAs
                                    cls_name = value_pattern.pattern.cls.id
                                    attribute_checks = " and ".join(
                                        transform_pattern(attr, True)
                                        for attr in value_pattern.pattern.patterns
                                    )
                                    match_class_condition = (
                                        f"isinstance({value_from_subject}, {cls_name})"
                                    )
                                    combined_condition = (
                                        f"{match_class_condition} and ({attribute_checks})"
                                        if attribute_checks
                                        else match_class_condition
                                    )
                                    compare_conditions.append(
                                        f"({transformed_key} in {subject}) and {combined_condition} and ({varname}.update({{{value_name!r}: {value_from_subject}}}) or True)"
                                    )
                                else:
                                    # Handling other patterns in MatchAs
                                    nested_pattern = transform_pattern(
                                        value_pattern.pattern, True
                                    )
                                    compare_conditions.append(
                                        f"({transformed_key} in {subject}) and ({value_from_subject} == {nested_pattern}) and ({varname}.update({{{repr(value_name)}: {value_from_subject}}}) or True)"
                                    )
                            else:
                                # Just variable binding without a nested pattern
                                compare_conditions.append(
                                    f"({transformed_key} in {subject}) and ({varname}.update({{{value_name!r}: {value_from_subject}}}) or True)"
                                )
                        elif isinstance(value_pattern, ast.MatchClass):
                            cls_name = value_pattern.cls.id
                            attribute_checks = " and ".join(
                                transform_pattern(attr, True)
                                for attr in value_pattern.patterns
                            )
                            match_class_condition = f"isinstance({subject}.get({transformed_key}), {cls_name})"
                            combined_condition = (
                                f"{match_class_condition} and ({attribute_checks})"
                                if attribute_checks
                                else match_class_condition
                            )
                            compare_conditions.append(
                                f"({transformed_key} in {subject}) and {combined_condition}"
                            )

                        else:
                            # Handle constant values for comparison
                            transformed_value = transform_pattern(value_pattern, True)
                            compare_conditions.append(
                                f"{transformed_key} in {subject} and {subject}.get({transformed_key}) == {transformed_value}"
                            )
                    if pattern.rest:
                        # If there's a "rest" key, capture all other keys in the dictionary
                        # Create a dictionary of key-value pairs not explicitly matched by the pattern
                        matched_keys = [
                            transform_pattern(key, True) for key in pattern.keys
                        ]
                        k_var = generate_variable_name()
                        v_var = generate_variable_name()
                        rest_dict = f"{{{k_var}: {v_var} for {k_var}, {v_var} in {subject}.items() if {k_var} not in [{', '.join(matched_keys)}]}}"
                        compare_conditions.append(
                            f"({varname}.update({{{pattern.rest!r}: {rest_dict}}}) or True)"
                        )
                    combined_conditions = " and ".join(compare_conditions)
                    return combined_conditions

                elif isinstance(pattern, ast.MatchStar):
                    return "True"
                elif isinstance(pattern, ast.Constant):
                    constant_value = repr(pattern.value)
                    return (
                        constant_value
                        if is_nested
                        else f"{subject} == {constant_value}"
                    )
                elif isinstance(pattern, ast.Name):
                    return pattern.id
                elif isinstance(pattern, ast.MatchAs):
                    name = pattern.name or "_"
                    as_condition = (
                        transform_pattern(pattern.pattern, is_nested)
                        if pattern.pattern
                        else "True"
                    )
                    return (
                        f"({varname}.update({{{name!r}: {subject}}}) or {as_condition})"
                    )
                elif isinstance(pattern, ast.MatchOr):
                    or_conditions = [
                        transform_pattern(p, True) for p in pattern.patterns
                    ]
                    return (
                        f"({' or '.join(or_conditions)})"
                        if is_nested
                        else f"{subject} == ({' or '.join(or_conditions)})"
                    )

                else:
                    raise NotImplementedError(
                        f"Pattern type {type(pattern)} not implemented"
                    )

            def transform_case(case: ast.match_case):
                condition = transform_pattern(case.pattern)
                guard_condition = (
                    f" and ({sans.transform_node(case.guard, current_loop_and_function, varname, scopes, exc_name, loop_vars)})"
                    if case.guard
                    else ""
                )
                body = ", ".join(
                    sans.transform_node(
                        stmt,
                        current_loop_and_function,
                        varname,
                        scopes,
                        exc_name,
                        loop_vars,
                    )
                    for stmt in case.body
                )
                return f"(lambda: ({condition}{guard_condition} and ({body})))()"

            cases = [transform_case(case) for case in node.cases]
            match_expression = " or ".join(cases)
            return prepend(f"({match_expression})")
        elif node is None:
            return "None"
        elif isinstance(node, ast.AugAssign):  # TODO: merge all ast.Assign conditions
            # Handling Augmented Assignment
            target = sans.transform_node(
                node.target,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            op = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.MatMult: "@",
                ast.Div: "/",
                ast.Mod: "%",
                ast.Pow: "**",
                ast.LShift: "<<",
                ast.RShift: ">>",
                ast.BitOr: "|",
                ast.BitXor: "^",
                ast.BitAnd: "&",
                ast.FloorDiv: "//",
            }[type(node.op)]
            # Converting AugAssign to a regular assignment
            # return f"{varname}.update({{{repr(target)}: {target} {op} {value}}})"
            if isinstance(node.target, ast.Attribute):
                return f"setattr({node.target.value.id}, {node.target.attr!r}, {target} {op} ({value}))"
            if check(
                [node.target],
                nonlocal_vars.get(current_loop_and_function[0]["name"], []),
            ):
                ctypes_var = generate_variable_name()
                item_var = generate_variable_name()
                i_var = generate_variable_name()
                return prepend(
                    f"[(lambda {ctypes_var}, {item_var}: {item_var} is not None and setattr({ctypes_var}.pythonapi.PyCell_Set, 'argtypes', [{ctypes_var}.py_object, {ctypes_var}.py_object]) or {ctypes_var}.pythonapi.PyCell_Set({item_var}, {ctypes_var}.py_object({value})))(__import__('ctypes'), next(({i_var} for {i_var} in {current_loop_and_function[0]['name']}.__closure__ if {i_var}.cell_contents == {node.targets[0].id}), None)), {node.targets[0].id} := {value}]"
                )
            return prepend(f"({target} := {target} {op} {value})")
        elif isinstance(node, ast.Delete):
            items = ",".join(
                f"({sans.transform_node(i, current_loop_and_function, varname, scopes, exc_name, loop_vars)})"
                for i in node.targets
            )
            name_references = {
                *(
                    i.id
                    for m in node.targets
                    for i in ast.walk(m)
                    if isinstance(i, ast.Name)
                    and isinstance(i.ctx, ast.Load)
                    and not hasattr(builtins, i.id)
                ),
                current_loop_and_function[0]["name"],
            }
            return prepend(
                f"exec({repr(f'del {items}')}, globals(), {{{(lambda s: s + ', ' if s else '')(', '.join(f'{i!r}: {i}' for i in name_references))}, **locals()}})"
            )
        elif isinstance(node, ast.With | ast.AsyncWith):
            with_items = [
                transform_with_item(
                    item,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for item in node.items
            ]
            body = [
                sans.transform_node(
                    stmt,
                    current_loop_and_function,
                    varname,
                    scopes,
                    exc_name,
                    loop_vars,
                )
                for stmt in node.body
            ]

            body = ", ".join([f"{expr}" for expr in body])

            with_statement = (
                f"{'async ' if isinstance(node, ast.AsyncWith) else ''}with "
                + ", ".join(i[0] for i in with_items)
                + ": "
                + "["
                + body
                + "]"
            )
            name_references = {
                *(
                    i.id
                    for m in node.body
                    for i in ast.walk(m)
                    if (
                        isinstance(i, ast.Name)
                        and isinstance(i.ctx, ast.Load)
                        and not hasattr(builtins, i.id)
                    )
                ),
                current_loop_and_function[0]["name"],
            }
            return prepend(
                f"exec({with_statement!r}, globals(), {{{(lambda s: s + ', ' if s else '')(', '.join(f'{i!r}: {i}' for i in name_references))}**locals()}})"
            )
        elif isinstance(node, ast.Global):
            # comma = ", "
            # return f"exec({repr(f'global {comma.join(i for i in node.names)}')}, globals(), locals())"
            for i in node.names:
                global_vars[current_loop_and_function[0]["name"]].append(i)
            return "None"
        elif isinstance(node, ast.Nonlocal):
            # comma = ", "
            # return f"exec({repr(f'nonlocal {comma.join(i for i in node.names)}')}, globals(), locals())"

            # print(nonlocal_helpers)
            for i in node.names:
                nonlocal_vars[current_loop_and_function[0]["name"]].append(i)
            return ", ".join(node.names)
            # return f"any(None for i in [[{', '.join(nonlocal_helpers[i] + '()' for i in node.names)}]] if [{', '.join(f'{i} := i[{m}]' for m, i in enumerate(node.names))}])"

            nodes = global_tree
            """get_module = lambda n: nodes.append(
                get_module(n.parent) if hasattr(n, "parent") else None
            )"""
            print(nodes)
            curr_func = next(
                filter(
                    lambda n: (
                        isinstance(n, ast.FunctionDef)
                        and n.name == current_loop_and_function[0]["name"]
                    ),
                    nodes,
                )
            )
            check_fname = lambda n: (
                n.name if isinstance(n, ast.FunctionDef) else check_fname(n.parent)
            )
            outer_name = check_fname(curr_func.parent)
            for i in node.names:
                nonlocal_vars[current_loop_and_function[0]["name"]].append(i)
            # return "None"
            # return f"any(None for i in [[{', '.join(current_loop_and_function[0]['name'] + f'.__closure__[{outer_name}.__code__.co_freevars.index({name!r})].cell_contents' for name in node.names)}]] if [{', '.join(f'{i} := i[{m}]' for m, i in enumerate(node.names))}])"
            current_fname = current_loop_and_function[0]["name"]
            return f"any(None for i in [[{', '.join(current_fname + f'.__closure__[{current_fname}.__code__.co_freevars.index({name!r})].cell_contents' for name in node.names)}]] if [{', '.join(f'{i} := i[{m}]' for m, i in enumerate(node.names))}])"

        elif isinstance(node, (ast.Yield, ast.YieldFrom)):
            return f"(yield{' ' if node.value else ''}{'from ' if isinstance(node, ast.YieldFrom) else ''}{sans.transform_node(node.value, current_loop_and_function, varname, scopes, exc_name, loop_vars) if node.value else ''})"
        elif isinstance(node, ast.Assert):
            test = sans.transform_node(
                node.test,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            msg = sans.transform_node(
                node.msg,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            # return f"exec({f'assert ({test}){msg_str}'!r})"
            return prepend(
                f"(_ for _ in ()).throw(AssertionError({msg if node.msg else ''}))"
            )
            # return f"(exec({f'raise AssertionError({msg if node.msg else empty_str})'!r}) if not ({test}) else None)"
        elif isinstance(node, ast.Await):
            return f"(yield from {sans.transform_node(node.value, current_loop_and_function, varname, scopes, exc_name, loop_vars)})"
        elif isinstance(node, ast.Is):
            return "is"
        elif isinstance(node, ast.NamedExpr):
            value = sans.transform_node(
                node.value,
                current_loop_and_function,
                varname,
                scopes,
                exc_name,
                loop_vars,
            )
            return f"({node.target.id} := {value})"
        else:
            raise NotImplementedError(f"Node type {type(node)} not implemented.")
        return ""


def transform_with_item(item: ast.withitem, *targs):
    context_expr = sans.transform_node(item.context_expr, *targs)
    optional_vars = sans.transform_node(item.optional_vars, *targs)
    return (
        f"{context_expr}{f' as {optional_vars}' if item.optional_vars else ''}",
        optional_vars,
    )


def annotate_parents(root):
    for node in ast.walk(root):
        for child in ast.iter_child_nodes(node):
            child.parent = node


# global_tree = []


def code_to_oneliner(code):
    # global global_tree
    global forbidden_names
    tree = ast.parse(code)
    print(ast.dump(tree, indent=2))
    annotate_parents(tree)
    forbidden_names = {
        (i.name if isinstance(i, ast.alias) else i.id)
        for i in ast.walk(tree)
        if isinstance(i, (ast.alias, ast.Name))
    }
    # global_tree = list(ast.walk(tree))
    # print(tree.body[0].body[0].body[0].parent.parent)
    # sans.func_dict = {}
    transformed_statements = [sans.transform_node(stmt) for stmt in tree.body]
    transformed_statements = [stmt for stmt in transformed_statements if stmt]

    slashn = ", "
    return f"({slashn.join(sans.imports_list + sans.pending_assignments + transformed_statements)})"


# Test
# code = open("bropiler.py").read()
code = """
import numpy as np
from collections import Counter

class KNN:
    def __init__(self, k=3):
        self.k = k

    def fit(self, X, y):
        self.X_train = X
        self.y_train = y

    def predict(self, X):
        y_pred = [self._predict(x) for x in X]
        return np.array(y_pred)

    def _predict(self, x):
        # Compute distances between x and all examples in the training set
        distances = [np.sqrt(np.sum((x_train - x) ** 2)) for x_train in self.X_train]
        # Sort by distance and return indices of the first k neighbors
        k_indices = np.argsort(distances)[:self.k]
        # Extract the labels of the k nearest neighbor training samples
        k_nearest_labels = [self.y_train[i] for i in k_indices]  
        # Return the most common class label
        most_common = Counter(k_nearest_labels).most_common(1)
        return most_common[0][0]

# Example of usage:
if __name__ == "__main__":
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split

    iris = load_iris()
    X, y = iris.data, iris.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)

    clf = KNN(k=3)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)

    # Calculate accuracy
    accuracy = np.mean(predictions == y_test)
    print(f"KNN classification accuracy: {accuracy}")


"""
code = """
class Hi:
  def __init__(self): self.a = "b"
print(Hi().a)
"""
code = """
from threading import Thread
def a(): print("hi")
e = Thread(target=a)
e.daemon = True
e.start()
"""
code = """
e = 1
def hi():
  global e
  e = 2
hi()
print(e)
"""
code = """
def one():
  e = 1
  def two():
    nonlocal e
    e = 2
  two()
  print(e)

one()
"""
code = """
a = [0]
a[0] = 1
print(a[0])
"""
code = """
a = 1
def hi():
  global a
  a = 2
hi()
print(a)
"""
code = """
def one():
  e = 1
  def two():
    nonlocal e
    e = 2
  two()
  print(e)

one()
"""
code = """
a = [1, 2, 3, 4, 5]
print(a[2:3])
"""
code = """
a = b = c = 1
print(a, b, c)
"""
code = """
a, b = c = 1, 2
"""
code = """
(a, b), (c, d) = (1, 2), [3, 4]
e, f = g = 1, 2
h = i = j = 50
lis = [67, 68]
m, n = lis
o = [1]
o[0] = 2
import threading
p = threading.Thread()
p.daemon = True
p.start(lambda: print("hi"))
"""
code = """
a = {}
a["b"] = 1
print(a)
c = {}
d, e = c["b"] = 1, 2
print(c)
f = {}
g, f["b"] = 3, 45
print(f)
"""
code = """
(a, b), (c, d) = (1, 2), [3, 4]
e, f = g = 1, 2
h = i = j = 50
lis = [67, 68]
m, n = lis
o = [1]
o[0] = 2
import threading
p = threading.Thread(target=lambda: print("hi"))
p.daemon = True
p.start()
print(locals())
"""
code = """
import numpy as np
from collections import Counter

class KNN:
    def __init__(self, k=3):
        self.k = k

    def fit(self, X, y):
        self.X_train = X
        self.y_train = y

    def predict(self, X):
        y_pred = [self._predict(x) for x in X]
        return np.array(y_pred)

    def _predict(self, x):
        # Compute distances between x and all examples in the training set
        distances = [np.sqrt(np.sum((x_train - x) ** 2)) for x_train in self.X_train]
        # Sort by distance and return indices of the first k neighbors
        k_indices = np.argsort(distances)[:self.k]
        # Extract the labels of the k nearest neighbor training samples
        k_nearest_labels = [self.y_train[i] for i in k_indices]  
        # Return the most common class label
        most_common = Counter(k_nearest_labels).most_common(1)
        return most_common[0][0]

# Example of usage:
if __name__ == "__main__":
    from sklearn.datasets import load_iris
    from sklearn.model_selection import train_test_split

    iris = load_iris()
    X, y = iris.data, iris.target
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=123)

    clf = KNN(k=3)
    clf.fit(X_train, y_train)
    predictions = clf.predict(X_test)

    # Calculate accuracy
    accuracy = np.mean(predictions == y_test)
    print(f"KNN classification accuracy: {accuracy}")


"""
code = """
import ctypes


def outer():
    a = 1

    def inner():
        ctypes.pythonapi.PyCell_Set.argtypes = [ctypes.py_object, ctypes.py_object]
        # ctypes.pythonapi.PyCell_Set.restype = ctypes.c_int
        ctypes.pythonapi.PyCell_Set(inner.__closure__[0], ctypes.py_object(a + 1))
        return a

    print(a)
    inner()
    print(a)
    a = 3
    inner()
    print(a)


outer()
"""
code = """
a = 1
def b():
  global a
  a = 2
b()
print(a)
"""
code = open("test_code.py", errors="ignore").read()
# def hi():
#  a = 1
#  print(a)
# hi()
# """
# print(code_to_oneliner(code))
with open("uhoh.py", "w") as f:
    f.write(code_to_oneliner(code))

import ast
from ..utils import (
    Context,
    Handle,
    TransformFunc,
    ensure_assign,
    generate_names,
    has_node,
    generate_name,
)


def loop_has_node(body: list[ast.stmt], target_type: type[ast.AST]) -> bool:
    boundaries = (ast.For, ast.While, ast.AsyncFor, ast.FunctionDef,
                  ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)

    def visit(node: ast.AST) -> bool:
        if isinstance(node, target_type):
            return True
        if isinstance(node, boundaries):
            return False
        return any(visit(child) for child in ast.iter_child_nodes(node))

    return any(visit(statement) for statement in body)


@Handle(ast.If)
def handle_if(node: ast.If, transform: TransformFunc, ctx: Context):
    test = transform(node.test)

    body_statements = [transform(stmt) for stmt in node.body]
    body = ", ".join(body_statements)

    orelse_statements = [transform(stmt) for stmt in node.orelse]
    orelse = ", ".join(orelse_statements) if orelse_statements else None
    if orelse:
        return f"([{body}] if ({test}) else [{orelse}])"
    else:
        return f"({test} and [{body}])"


@Handle(ast.IfExp)
def handle_ifexp(node: ast.IfExp, transform: TransformFunc, ctx: Context):
    test = transform(node.test)
    body = transform(node.body)
    orelse = transform(node.orelse)
    return f"({body} if {test} else {orelse})"


@Handle(ast.For)
def handle_for(node: ast.For, transform: TransformFunc, ctx: Context):
    has_break = loop_has_node(node.body, ast.Break)
    has_continue = loop_has_node(node.body, ast.Continue)

    iter_ = transform(node.iter)
    orelse_statements = [f"({transform(stmt)})" for stmt in node.orelse]
    orelse = ", ".join(orelse_statements) if orelse_statements else None

    prev_break_var = ctx.break_var
    prev_continue_var = ctx.continue_var
    prev_in_loop = ctx.in_loop
    ctx.in_loop = True
    

    if has_break:
        break_var = generate_name(prefix="__break_for_")
        ctx.break_var = break_var

    if has_continue:
        continue_var = generate_name(prefix="__continue_for_")
        ctx.continue_var = continue_var

    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    body = ", ".join(body_statements)

    result: list[str] = ["(["]

    if has_break:
        result.append(f"({ctx.break_var} := False), ")
        iterator_var, sentinel_var = generate_names(2, prefix="__for_iterator_")
        result.append(f"({iterator_var} := iter({iter_})), ({sentinel_var} := object()), ")
        iter_ = (
            f"iter(lambda: {sentinel_var} if {ctx.break_var} else "
            f"next({iterator_var}, {sentinel_var}), {sentinel_var})"
        )

    result.append("[[")
    # print(ctx.assignment_temp_vars)
    ctx.assignment_temp_vars.clear()
    prev_should = ctx.should_assign_nonnames_to_temp
    ctx.should_assign_nonnames_to_temp = False
    target = transform(node.target)
    ctx.should_assign_nonnames_to_temp = prev_should
    # print(ctx.assignment_temp_vars)
    target_assigns = ", ".join(
        ensure_assign(transform(real), mangled, ctx)
        # f"({transform(real)} := {mangled})"
        for real, mangled in ctx.assignment_temp_vars.items()
    )
    if target_assigns:
        result.append(target_assigns + ", ")
    if has_continue:
        result.append(f"({ctx.continue_var} := False), ")

    result.append(body)
    result.append("]")

    result.append(f" for {target} in {iter_}")
    result.append("]]")

    if orelse:
        if has_break:
            result.append(f", {ctx.break_var} or [{orelse}]")
        else:
            result.append(f", [{orelse}]")

    result.append(")")

    ctx.break_var = prev_break_var
    ctx.continue_var = prev_continue_var
    ctx.in_loop = prev_in_loop
    ctx.assignment_temp_vars.clear()

    return "".join(result)


@Handle(ast.While)
def handle_while(node: ast.While, transform: TransformFunc, ctx: Context):
    has_break = loop_has_node(node.body, ast.Break)
    has_continue = loop_has_node(node.body, ast.Continue)

    test = transform(node.test)
    orelse_statements = [f"({transform(stmt)})" for stmt in node.orelse]
    orelse = ", ".join(orelse_statements) if orelse_statements else None

    prev_break_var = ctx.break_var
    prev_continue_var = ctx.continue_var
    prev_in_loop = ctx.in_loop
    ctx.in_loop = True


    if has_break:
        break_var = generate_name(prefix="__break_while_")
        ctx.break_var = break_var

    if has_continue:
        continue_var = generate_name(prefix="__continue_while_")
        ctx.continue_var = continue_var

    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    if has_continue:
        body_statements.insert(0, f"({ctx.continue_var} := False)")
    body = "[" + ", ".join(body_statements) + "]"

    inf_var, test_var = generate_names(2, prefix="__unused_loop_while_")
    body_var = generate_name(prefix="__body_while_")

    result: list[str] = ["["]

    if has_break:
        result.append(f"({ctx.break_var} := False), ")

    if has_continue:
        result.append(f"({ctx.continue_var} := False), ")

    condition_var = generate_name(prefix="__while_condition_")
    result.append(f"{body_var} := (([{condition_var} := {test}, bool({condition_var}) and {body}")

    if has_break:
        result.append(f" and not {ctx.break_var}")

    result.append(f"][-1]) for {inf_var} in iter(int, 1)), ")

    result.append(f"[None for {test_var} in iter(lambda: next({body_var}), False)]")

    if orelse:
        result.append(f", {ctx.break_var} or [{orelse}]]" if has_break else f", [{orelse}]]")
    else:
        result.append("]")

    ctx.break_var = prev_break_var
    ctx.continue_var = prev_continue_var
    ctx.in_loop = prev_in_loop

    return "".join(result)


@Handle(ast.Break)
def handle_break(node: ast.Break, transform: TransformFunc, ctx: Context):
    if ctx.break_var is None:
        raise SyntaxError("break statement not inside a loop")
    return f"[{ctx.break_var} := True]"


@Handle(ast.Continue)
def handle_continue(node: ast.Continue, transform: TransformFunc, ctx: Context):
    if ctx.continue_var is None:
        raise SyntaxError("continue statement not inside a loop")
    return f"({ctx.continue_var} := True)"


@Handle(ast.Raise)
def handle_raise(node: ast.Raise, transform: TransformFunc, ctx: Context):
    temp_name = generate_name(prefix="__raise_")
    exc = transform(node.exc) if node.exc else "__import__('sys').exc_info()[1]"
    cause = transform(node.cause) if node.cause else "None"
    if node.cause:
        return f"(_ for _ in ()).throw(setattr(({temp_name} := {exc}), '__cause__', {cause}) or {temp_name})"
    else:
        return f"(_ for _ in ()).throw({exc})"


@Handle(ast.Assert)
def handle_assert(node: ast.Assert, transform: TransformFunc, ctx: Context):
    test = transform(node.test)
    msg = transform(node.msg) if node.msg else "''"
    return f"{test} or (_ for _ in ()).throw(AssertionError({msg}))"


def handle_with_item(items: list[ast.withitem], i: int, body: str, transform: TransformFunc, *, is_async: bool):
    if i >= len(items):
        return body
    
    item = items[i]
    manager_var = generate_name(prefix="__with_manager_")
    exit_var = generate_name(prefix="__with_exit_")
    value_var = generate_name(prefix="__with_value_")
    # hit_except_var = generate_name(prefix="__with_hit_")

    body_var = generate_name(prefix=f"__with_body_{i}_")
    unused_body_for_var = generate_name(prefix="__unused_for_body_with_")
    self_var = generate_name(prefix="__self_")
    exception_type_var = generate_name(prefix="__exception_type_")
    exception_var = generate_name(prefix="__exception_")
    traceback_var = generate_name(prefix="__traceback_")

    context_expr = transform(item.context_expr)
    # is_async = isinstance(node, ast.AsyncWith)
    enter_method = "__aenter__" if is_async else "__enter__"
    exit_method = "__aexit__" if is_async else "__exit__"

    # body_statements = [f"({transform(stmt)})" for stmt in node.body]
    # body = ", ".join(body_statements)
    body = handle_with_item(items, i + 1, body, transform, is_async=is_async)

    if item.optional_vars:
        assign_node = ast.Assign(
            targets=[item.optional_vars],
            value=ast.Name(id=value_var, ctx=ast.Load())
        )
        assign_code = transform(assign_node) + ", "
    else:
        assign_code = ""

    body_assign = f"({body_var} := ([{assign_code}{body}] for {unused_body_for_var} in [0]))"

    preparation = f"[{manager_var} := ({context_expr}), {exit_var} := {manager_var}.{exit_method}, {value_var} := {manager_var}.{enter_method}()]"
    
    exit_lambda = f"lambda {self_var}, {exception_type_var}, {exception_var}, {traceback_var}: {exit_var}({exception_type_var}, {exception_var}, {traceback_var})"

    try_stmt = f'type({repr(f"__With_{i}")}, (__import__("contextlib").ContextDecorator,), {{"__enter__": lambda {self_var}: {self_var}, "__exit__": {exit_lambda}}})()(lambda: (*{body_var},))()' # TODO lol

    with_code = f"{body_assign}, {preparation}, {try_stmt}"

    return with_code

@Handle(ast.With, ast.AsyncWith)
def handle_with(node: ast.With | ast.AsyncWith, transform: TransformFunc, ctx: Context):
    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    body = ", ".join(body_statements)
    
    return handle_with_item(node.items, 0, body, transform, is_async=isinstance(node, ast.AsyncWith))


    


@Handle(ast.Try)
def handle_try(node: ast.Try, transform: TransformFunc, ctx: Context):
    try_body = "[" + ", ".join(transform(stmt) for stmt in node.body) + "] for _ in [0]"

    handlers = []
    for handler in node.handlers:
        exc_type = transform(handler.type) if handler.type else None
        exc_var = handler.name or generate_name(prefix="__exc_")
        handler_body = "[" + ", ".join(transform(stmt) for stmt in handler.body) + "]"
        handlers.append((exc_type, exc_var, handler_body))

    orelse_body = ""
    if node.orelse:
        orelse_body = "[" + ", ".join(transform(stmt) for stmt in node.orelse) + "]"
        else_iter_variable = generate_name(prefix="__try_orelse_unused_")
        else_variable = generate_name(prefix="__try_else_")

    finalbody = ""
    if node.finalbody:
        finalbody = "[" + ", ".join(transform(stmt) for stmt in node.finalbody) + "]"
        final_iter_variable = generate_name(prefix="__try_finally_unused_")
        finally_variable = generate_name(prefix="__try_finally_")

    exc_variable = generate_name(prefix="__try_exc_")
    try_variable = generate_name(prefix="__try_body_")
    exc_in_exit_var = generate_name(prefix="__try_exc_exit_")
    unused_exc_type_var = generate_name(prefix="__try_exc_type_unused_")
    self_var = generate_name(prefix="__try_self_")
    unused_traceback_var = generate_name(prefix="__try_last_exit_unused_")
    class_name = generate_name(prefix="__TryExcept_")

    handler_vars = [generate_name(prefix="__handler_") for _ in handlers]

    handlers_code = ", ".join(
        f"({hv} := ({body} for {ev} in {exc_variable}))"
        for hv, (exc_type, ev, body) in zip(handler_vars, handlers)
    )

    orelse_code = (
        f"{else_variable} := ({orelse_body} for {else_iter_variable} in [0]), "
        if orelse_body
        else ""
    )
    finally_code = (
        f"{finally_variable} := ({finalbody} for {final_iter_variable} in [0]), "
        if finalbody
        else ""
    )

    handler_checks = "None"
    for handler_var, (exc_type, _, _) in reversed(list(zip(handler_vars, handlers))):
        if exc_type:
            handler_checks = f"((*{handler_var},) if isinstance({exc_in_exit_var}, {exc_type}) else ({handler_checks}))"
        else:
            handler_checks = f"(*{handler_var},)"

    handled_var = generate_name(prefix="__try_handled_")
    handler_result = f"({handled_var} := ({handler_checks}))"
    if finalbody:
        handler_result = f"({handler_result}, (*{finally_variable},), bool({handled_var}))[-1]"
    else:
        handler_result = f"bool({handler_result})"
    exit_lambda = f"lambda {self_var}, {unused_exc_type_var}, {exc_in_exit_var}, {unused_traceback_var}: {exc_in_exit_var} is not None and ({exc_variable}.append({exc_in_exit_var}) or {handler_result})"

    result_parts = [f"*{try_variable}"]
    if orelse_body:
        result_parts.append(f"*{else_variable}")
    if finalbody:
        result_parts.append(f"*{finally_variable}")
    result_tuple = ", ".join(result_parts) + ","

    setup = ", ".join(part for part in (
        f"{exc_variable} := []", f"{try_variable} := ({try_body})",
        handlers_code, orelse_code.rstrip(", "), finally_code.rstrip(", "),
    ) if part)
    try_except_func = f"""(\
{setup}, type("{class_name}", (__import__("contextlib").ContextDecorator,), {{\
"__enter__": lambda {self_var}: {self_var}, \
"__exit__": {exit_lambda}\
}})()(lambda: ({result_tuple}))())"""

    return try_except_func


def transform_pattern(
    pattern: ast.pattern, subject: str, transform: TransformFunc, ctx: Context
):

    if isinstance(pattern, ast.MatchOr):
        return "(" + " or ".join(
            f"({transform_pattern(p, subject, transform, ctx)})"
            for p in pattern.patterns
        ) + ")"
    elif isinstance(pattern, ast.MatchAs):
        as_condition = (
            transform_pattern(pattern.pattern, subject, transform, ctx)
            if pattern.pattern
            else "True"
        )
        if pattern.name is None:
            return as_condition
        assignment = ensure_assign(pattern.name, subject, ctx, in_match=True)
        return f"({as_condition}) and {assignment}" if pattern.pattern else assignment
    elif isinstance(pattern, ast.MatchSingleton):
        return f"{subject} is {pattern.value!r}"
    elif isinstance(pattern, ast.MatchValue):
        comparison_value = transform(pattern.value)
        op = (
            "is"
            if isinstance(pattern.value, ast.Constant)
            and any(pattern.value.value is x for x in (None, True, False))
            else "=="
        )
        return f"{subject} {op} {comparison_value}"
    elif isinstance(pattern, ast.MatchSequence):
        collections_var = generate_name(prefix="__collections_")
        is_fixed_length = not has_node(pattern, ast.MatchStar)
        parts = [
            f"isinstance({subject}, (({collections_var} := __import__('collections', fromlist=('abc', 'deque'))).abc.Sequence, __import__('array').array, {collections_var}.deque, list, memoryview, range, tuple)) and not isinstance({subject}, (str, bytes, bytearray))"
        ]
        if is_fixed_length:
            parts.append(f"len({subject}) == {len(pattern.patterns)}")
            parts += [
                transform_pattern(el, f"{subject}[{i}]", transform, ctx)
                for i, el in enumerate(pattern.patterns)
            ]
        else:
            star_index = next(i for i, el in enumerate(pattern.patterns)
                              if isinstance(el, ast.MatchStar))
            leading_no_star = pattern.patterns[:star_index]
            star_pattern = pattern.patterns[star_index]
            trailing_no_star = pattern.patterns[star_index + 1:]

            parts.append(f"len({subject}) >= {len(leading_no_star) + len(trailing_no_star)}")
            parts += [
                transform_pattern(el, f"{subject}[{i}]", transform, ctx)
                for i, el in enumerate(leading_no_star)
            ]
            slice_end = f"-{len(trailing_no_star)}" if trailing_no_star else ""
            parts.append(
                transform_pattern(
                    star_pattern,
                    f"{subject}[{len(leading_no_star)}:{slice_end}]",
                    transform,
                    ctx,
                )
            )
            parts += [
                transform_pattern(
                    el, f"{subject}[-{len(trailing_no_star) - i}]", transform, ctx
                )
                for i, el in enumerate(trailing_no_star)
            ]

        return " and ".join(parts)
    elif isinstance(pattern, ast.MatchStar):
        if pattern.name:
            return ensure_assign(pattern.name, subject, ctx, in_match=True)
            # return f"({pattern.name} := {subject})"
        else:
            return "True"
    elif isinstance(pattern, ast.MatchMapping):
        parts = [
            f"isinstance({subject}, (__import__('collections', fromlist=('abc',)).abc.Mapping, dict, type(type.__dict__)))"
        ]
        for key, value_pattern in zip(pattern.keys, pattern.patterns):
            transformed_key = transform(key)
            value_subject = f"{subject}.get({transformed_key}, None)"
            parts.append(f"{transformed_key} in {subject}")
            parts.append(
                transform_pattern(value_pattern, value_subject, transform, ctx)
            )
        if pattern.rest:
            rest_subject = f"{{k: v for k, v in {subject}.items() if k not in {{{', '.join(transform(key) for key in pattern.keys)}}}}}"
            # parts.append(f"({pattern.rest} := {rest_subject})")
            parts.append(ensure_assign(pattern.rest, rest_subject, ctx, in_match=True))
        return " and ".join(parts)
    elif isinstance(pattern, ast.MatchClass):
        # uh oh
        # we're trusting the user to make it a class, we're not raising TypeError if it's not an instance of type
        parts = [f"isinstance({subject}, {transform(pattern.cls)})"]
        # TODO support special types
        if pattern.patterns:
            match_args_var = generate_name(prefix="__match_args_")
            parts.append(
                f"({match_args_var} := getattr({subject}, '__match_args__', ()))"
            )
            for i, attr_pattern in enumerate(pattern.patterns):
                # we won't be raising errors, we trust the user
                attr_subject = f"getattr({subject}, {match_args_var}[{i}])"
                parts.append(f"hasattr({subject}, {match_args_var}[{i}])")
                parts.append(
                    transform_pattern(attr_pattern, attr_subject, transform, ctx)
                )
        for kwd_attr, kwd_pattern in zip(pattern.kwd_attrs, pattern.kwd_patterns):
            attr_subject = f"getattr({subject}, {kwd_attr!r})"
            parts.append(f"hasattr({subject}, {kwd_attr!r})")
            parts.append(transform_pattern(kwd_pattern, attr_subject, transform, ctx))
        return " and ".join(parts)

    raise SyntaxError("unreachable")

@Handle(ast.Match)
def handle_match(node: ast.Match, transform: TransformFunc, ctx: Context):
    subject = transform(node.subject)

    subject_var = generate_name(prefix="__match_subject_")

    branches = []
    for case in node.cases:
        condition = transform_pattern(case.pattern, subject_var, transform, ctx)
        if case.guard:
            condition = f"({condition}) and ({transform(case.guard)})"
        body = ", ".join(transform(stmt) for stmt in case.body)
        branches.append((condition, body))

    # A match chooses the first successful case. Nesting conditional
    # expressions keeps later patterns and guards unevaluated after a match.
    cases = "None"
    for condition, body in reversed(branches):
        cases = f"([{body}] if ({condition}) else {cases})"

    return f"[({subject_var} := {subject}), {cases}]"

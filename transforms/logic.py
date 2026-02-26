import ast
import itertools
from utils import (
    Context,
    Handle,
    TransformFunc,
    generate_names,
    has_node,
    generate_name,
)


@Handle(ast.If)
def handle_if(node: ast.If, transform: TransformFunc, ctx: Context):
    test = transform(node.test)

    body_statements = [transform(stmt) for stmt in node.body]
    body = ", ".join(body_statements)

    orelse_statements = [transform(stmt) for stmt in node.orelse]
    orelse = ", ".join(orelse_statements) if orelse_statements else None
    if orelse:
        return f"([{body}] if ({test}) else [{orelse}])"  # TODO maybe change [] to () because tuple looks cooler
    else:
        return f"({test} and {body})"


@Handle(ast.IfExp)
def handle_ifexp(node: ast.IfExp, transform: TransformFunc, ctx: Context):
    test = transform(node.test)
    body = transform(node.body)
    orelse = transform(node.orelse)
    return f"({body} if {test} else {orelse})"


@Handle(ast.For)
def handle_for(node: ast.For, transform: TransformFunc, ctx: Context):
    has_break = has_node(node, ast.Break)
    has_continue = has_node(node, ast.Continue)

    prev_break_var = ctx.break_var
    prev_continue_var = ctx.continue_var

    if has_break:
        break_var = generate_name(prefix="__break_for_")
        ctx.break_var = break_var

    if has_continue:
        continue_var = generate_name(prefix="__continue_for_")
        ctx.continue_var = continue_var

    iter_ = transform(node.iter)
    target = transform(node.target)
    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    body = ", ".join(body_statements)

    orelse_statements = [
        f"({transform(stmt)})" for stmt in node.orelse
    ]  # TODO make orelse
    orelse = ", ".join(orelse_statements) if orelse_statements else None

    result: list[str] = ["(["]

    if has_break:
        result.append(f"({ctx.break_var} := False), ")

    result.append("[[")
    if has_continue:
        result.append(f"({ctx.continue_var} := False), ")

    result.append(body)
    result.append("]")

    result.append(f" for {target} in {iter_}")
    result.append("]]")

    if orelse:
        result.append(f", {ctx.break_var} or [{orelse}]")

    # result.append(f", ({target} := )")
    # TODO make target available in scope
    result.append(")")

    ctx.break_var = prev_break_var
    ctx.continue_var = prev_continue_var

    return "".join(result)


@Handle(ast.While)
def handle_while(node: ast.While, transform: TransformFunc, ctx: Context):
    has_break = has_node(node, ast.Break)
    has_continue = has_node(node, ast.Continue)

    prev_break_var = ctx.break_var
    prev_continue_var = ctx.continue_var

    if has_break:
        break_var = generate_name(prefix="__break_while_")
        ctx.break_var = break_var

    if has_continue:
        continue_var = generate_name(prefix="__continue_while_")
        ctx.continue_var = continue_var

    test = transform(node.test)
    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    body = "[" + ", ".join(body_statements) + "]"

    inf_var, test_var = generate_names(2, prefix="__unused_loop_while_")
    body_var = generate_name(prefix="__body_while_")

    orelse_statements = [
        f"({transform(stmt)})" for stmt in node.orelse
    ]  # TODO make orelse
    orelse = ", ".join(orelse_statements) if orelse_statements else None

    result: list[str] = ["["]

    if has_break:
        result.append(f"({ctx.break_var} := False), ")

    if has_continue:
        result.append(f"({ctx.continue_var} := False), ")

    result.append(f"{body_var} := (({body} and ")

    if has_break:
        result.append(f"not {ctx.break_var} and ")

    result.append(f"{test}) for {inf_var} in iter(int, 1)), ")

    result.append(f"[None for {test_var} in iter(lambda: next({body_var}), False)]")

    if orelse:
        result.append(f", {ctx.break_var} or [{orelse}]]")
    else:
        result.append("]")

    ctx.break_var = prev_break_var
    ctx.continue_var = prev_continue_var

    return "".join(result)


@Handle(ast.Break)
def handle_break(node: ast.Break, transform: TransformFunc, ctx: Context):
    if ctx.break_var is None:
        raise SyntaxError("break statement not inside a loop")
    return f"({ctx.break_var} := True)"


@Handle(ast.Continue)
def handle_continue(node: ast.Continue, transform: TransformFunc, ctx: Context):
    if ctx.continue_var is None:
        raise SyntaxError("continue statement not inside a loop")
    return f"({ctx.continue_var} := True)"


@Handle(ast.Raise)
def handle_raise(node: ast.Raise, transform: TransformFunc, ctx: Context):
    # TODO from
    temp_name = generate_name(prefix="__raise_")
    exc = transform(node.exc) if node.exc else "None"
    cause = transform(node.cause) if node.cause else "None"
    if node.cause:
        return f"(_ for _ in ()).throw(setattr(({temp_name} := {exc}()), '__cause__', {cause}) or {temp_name})"
    else:
        return f"(_ for _ in ()).throw({exc})"


@Handle(ast.Assert)
def handle_assert(node: ast.Assert, transform: TransformFunc, ctx: Context):
    test = transform(node.test)
    msg = transform(node.msg) if node.msg else "''"
    return f"{test} or (_ for _ in ()).throw(AssertionError({msg}))"


@Handle(ast.With, ast.AsyncWith)
def handle_with(node: ast.With | ast.AsyncWith, transform: TransformFunc, ctx: Context):
    # TODO
    if len(node.items) > 1:
        if isinstance(node, ast.AsyncWith):
            inner_with = ast.AsyncWith(
                items=node.items[1:],
                body=node.body,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
            outer_with = ast.AsyncWith(
                items=[node.items[0]],
                body=[inner_with],
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
        else:
            inner_with = ast.With(
                items=node.items[1:],
                body=node.body,
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
            outer_with = ast.With(
                items=[node.items[0]],
                body=[inner_with],
                lineno=node.lineno,
                col_offset=node.col_offset,
            )
        return transform(outer_with)

    item = node.items[0]
    manager_var = generate_name(prefix="__with_manager_")
    enter_var = generate_name(prefix="__with_enter_")
    exit_var = generate_name(prefix="__with_exit_")
    value_var = generate_name(prefix="__with_value_")
    hit_except_var = generate_name(prefix="__with_hit_")

    context_expr = transform(item.context_expr)
    is_async = isinstance(node, ast.AsyncWith)
    enter_method = "__aenter__" if is_async else "__enter__"
    exit_method = "__aexit__" if is_async else "__exit__"

    body_statements = [f"({transform(stmt)})" for stmt in node.body]
    body = ", ".join(body_statements)

    target_code = ""
    if item.optional_vars:
        if isinstance(item.optional_vars, ast.Name):
            target_code = f"{item.optional_vars.id} := {value_var}, "
        elif isinstance(item.optional_vars, (ast.Tuple, ast.List)):
            target_code = f"{transform(item.optional_vars)} := {value_var}, "

    with_code = f"""(
{manager_var} := {context_expr},
{enter_var} := type({manager_var}).{enter_method},
{exit_var} := type({manager_var}).{exit_method},
{value_var} := {enter_var}({manager_var}),
{hit_except_var} := False,
{target_code}[{body} for _ in [0]]
)[-1]"""

    return with_code


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
    unused_last_exit_var = generate_name(prefix="__try_last_exit_unused_")
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

    handler_checks = (
        " ".join(
            f"(*{handler_vars[i]},) "
            + (
                f"if isinstance({exc_in_exit_var}, {exc_type}) else "
                if exc_type
                else ""
            )
            for i, (exc_type, _, _) in enumerate(handlers)
        )
        + "None"
    )

    exit_lambda = f"""lambda {self_var}, {unused_exc_type_var}, {exc_in_exit_var}, {unused_last_exit_var}: {exc_in_exit_var} and ({exc_variable}.append({exc_in_exit_var}) or ({handler_checks}{finalbody and f' and (*{finally_variable},)'}))"""

    try_except_func = f"""(\
{exc_variable} := [], {try_variable} := ({try_body}), \
{handlers_code}, \
{orelse_code}{finally_code}type("{class_name}", (__import__("contextlib").ContextDecorator,), {{\
"__enter__": lambda {self_var}: {self_var}, \
"__exit__": {exit_lambda}\
}})()(lambda: (*{try_variable},{orelse_body and f' *{else_variable}'}{finalbody and (f', *{finally_variable}' if orelse_body else f', *{finally_variable}')}))())"""

    return try_except_func


def transform_pattern(
    pattern: ast.pattern, subject: str, transform: TransformFunc, ctx: Context
):

    if isinstance(pattern, ast.MatchOr):
        return " or ".join(
            transform_pattern(p, subject, transform, ctx) for p in pattern.patterns
        )
    elif isinstance(pattern, ast.MatchAs):
        name = pattern.name or "_"
        as_condition = (
            transform_pattern(pattern.pattern, subject, transform, ctx)
            if pattern.pattern
            else "True"
        )
        return (
            f"{as_condition} and ({name} := {subject})"
            if pattern.pattern
            else f"({name} := {subject})"
        )
    elif isinstance(pattern, ast.MatchValue):
        comparison_value = transform(pattern.value)
        op = (
            "is"
            if isinstance(pattern.value, ast.Constant)
            and pattern.value.value in (None, True, False)
            else "=="
        )
        return f"{subject} {op} {comparison_value}"
    elif isinstance(pattern, ast.MatchSequence):
        collections_var = generate_name(prefix="__collections_")
        is_fixed_length = not has_node(pattern, ast.MatchStar)
        parts = [
            f"isinstance({subject}, (({collections_var} := __import__('collections')).abc.Sequence, __import__('array').array, {collections_var}.deque, list, memoryview, range, tuple) and not isinstance({subject}, (str, bytes, bytearray)) )"
        ]
        if is_fixed_length:
            parts.append(f"len({subject}) == {len(pattern.patterns)}")
            parts += [
                transform_pattern(el, f"{subject}[{i}]", transform, ctx)
                for i, el in enumerate(pattern.patterns)
            ]
        else:
            non_star = [
                (i, el)
                for i, el in enumerate(pattern.patterns)
                if not isinstance(el, ast.MatchStar)
            ]
            leading_no_star = list(
                itertools.takewhile(
                    lambda el: not isinstance(el, ast.MatchStar), pattern.patterns
                )
            )
            star_pattern = next(
                (el for el in pattern.patterns if isinstance(el, ast.MatchStar))
            )
            trailing_no_star = list(
                itertools.dropwhile(
                    lambda el: not isinstance(el, ast.MatchStar), pattern.patterns
                )
            )

            parts.append(f"len({subject}) >= {len(non_star)}")
            parts += [
                transform_pattern(el, f"{subject}[{i}]", transform, ctx)
                for i, el in enumerate(leading_no_star)
            ]
            parts.append(
                transform_pattern(
                    star_pattern,
                    f"{subject}[{len(leading_no_star)}:{len(pattern.patterns) - len(trailing_no_star)}]",
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
            return f"({pattern.name} := {subject})"  # TODO if subject is falsey, this will fail
        else:
            return "True"
    elif isinstance(pattern, ast.MatchMapping):
        # TODO find out how rest parameter works
        parts = [
            f"isinstance({subject}, (__import__('collections').abc.Mapping, dict, type(type.__dict__)))"
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
            parts.append(f"({pattern.rest} := {rest_subject})")
        return " and ".join(parts)
    elif isinstance(pattern, ast.MatchClass):
        # uh oh
        # we're trusting the user to make it a class, we're not raising TypeError if it's not an instance of type
        parts = [f"isinstance({subject}, {transform(pattern.cls)})"]
        # TODO support special types
        if pattern.patterns:
            match_args_var = generate_name(prefix="__match_args_")
            parts.append(
                f"({match_args_var} := getattr({subject}, '__match_args__', None))"
            )
            for i, attr_pattern in enumerate(pattern.patterns):
                # we won't be raising errors, we trust the user
                attr_subject = f"{match_args_var}[{i}]"
                parts.append(
                    transform_pattern(attr_pattern, attr_subject, transform, ctx)
                )
        for kwd_attr, kwd_pattern in zip(pattern.kwd_attrs, pattern.kwd_patterns):
            attr_subject = f"getattr({subject}, {kwd_attr!r}, None)"
            parts.append(transform_pattern(kwd_pattern, attr_subject, transform, ctx))
        return " and ".join(parts)
    # elif isinstance(pattern, ast.MatchSingleton):
    #     comparison_value = repr(pattern.value)
    #     return f"{subject} is {comparison_value}"

    # elif isinstance(pattern, ast.Match)

    return "Hi"
    # from utils import generate_name

    # if isinstance(pattern, ast.MatchValue):
    #     comparison_value = transform(pattern.value)
    #     return comparison_value if is_nested else f"{subject} == {comparison_value}"
    # elif isinstance(pattern, ast.MatchSingleton):
    #     comparison_value = repr(pattern.value)
    #     return comparison_value if is_nested else f"{subject} is {comparison_value}"
    # elif isinstance(pattern, ast.MatchSequence):
    #     sequence_conditions = []
    #     star = False
    #     for i, el in enumerate(pattern.patterns):
    #         if isinstance(el, ast.MatchAs) and el.pattern is None:
    #             name = el.name or "_"
    #             sequence_conditions.append(f"[({name} := {subject}[{i}])] or True")
    #         elif isinstance(el, ast.MatchAs):
    #             name = el.name or "_"
    #             as_condition = transform_pattern(
    #                 el.pattern, subject, transform, ctx, is_nested
    #             )
    #             sequence_conditions.append(
    #                 f"[({name} := {subject}[{i}]), {as_condition}][-1]"
    #             )
    #         elif isinstance(el, ast.MatchOr):
    #             or_conditions = [
    #                 f"{subject}[{i}] == {transform_pattern(p, subject, transform, ctx, True)}"
    #                 for p in el.patterns
    #             ]
    #             sequence_conditions.append(f"({' or '.join(or_conditions)})")
    #         elif isinstance(el, ast.MatchStar):
    #             star = True
    #             break
    #         else:
    #             seq_pattern = transform_pattern(el, subject, transform, ctx, True)
    #             sequence_conditions.append(f"{subject}[{i}] == {seq_pattern}")
    #     length_check = (
    #         f"(len({subject}) {'>=' if star else '=='} {len(pattern.patterns)})"
    #     )
    #     combined_conditions = " and ".join(sequence_conditions)
    #     return f"({length_check} and ({combined_conditions}))"
    # elif isinstance(pattern, ast.MatchClass):
    #     cls_name = pattern.cls.id
    #     attribute_conditions = []
    #     keyword_patterns = [
    #         f"{subject}.{kwd_attr} == {transform_pattern(kwd_pattern, subject, transform, ctx, True)}"
    #         for kwd_attr, kwd_pattern in zip(pattern.kwd_attrs, pattern.kwd_patterns)
    #     ]
    #     for i, attr_pattern in enumerate(pattern.patterns):
    #         if isinstance(attr_pattern, ast.MatchAs):
    #             name = attr_pattern.name or "_"
    #             if attr_pattern.pattern:
    #                 nested_pattern = transform_pattern(
    #                     attr_pattern.pattern, subject, transform, ctx, True
    #                 )
    #                 attribute_conditions.append(
    #                     f"({nested_pattern} and ({name} := getattr({subject}, {attr_pattern.name!r})))"
    #                 )
    #             else:
    #                 attribute_conditions.append(
    #                     f"({name} := getattr({subject}, {attr_pattern.name!r}))"
    #                 )
    #         elif isinstance(attr_pattern, ast.MatchValue):
    #             comparison_value = transform_pattern(
    #                 attr_pattern.value, subject, transform, ctx, True
    #             )
    #             attribute_conditions.append(
    #                 f"{comparison_value} == getattr({subject}, '__class__')"
    #             )
    #         else:
    #             raise NotImplementedError(
    #                 f"Attribute pattern type {type(attr_pattern)} not implemented in MatchClass"
    #             )
    #     instance_check = f"i    # def transform_case(case: ast.match_case):


# sinstance({subject}, {cls/_name})"
#     attribute_conditions.append("True")
#     combined_conditions = " and ".join(attribute_conditions + keyword_patterns)
#     return f"{instance_check} and ({combined_conditions})"
# elif isinstance(pattern, ast.MatchMapping):
#     compare_conditions = []
#     for key, value_pattern in zip(pattern.keys, pattern.patterns):
#         transformed_key = transform_pattern(key, subject, transform, ctx, True)
#         if isinstance(value_pattern, ast.MatchAs):
#             value_name = value_pattern.name or "_"
#             value_from_subject = f"{subject}.get({transformed_key})"
#             if value_pattern.pattern:
#                 nested_pattern = transform_pattern(
#                     value_pattern.pattern, subject, transform, ctx, True
#                 )
#                 compare_conditions.append(
#                     f"({transformed_key} in {subject}) and ({value_from_subject} == {nested_pattern}) and ({value_name} := {value_from_subject})"
#                 )
#             else:
#                 compare_conditions.append(
#                     f"({transformed_key} in {subject}) and ({value_name} := {value_from_subject})"
#                 )
#         else:
#             transformed_value = transform_pattern(
#                 value_pattern, subject, transform, ctx, True
#             )
#             compare_conditions.append(
#                 f"{transformed_key} in {subject} and {subject}.get({transformed_key}) == {transformed_value}"
#             )
#     if pattern.rest:
#         matched_keys = [
#             transform_pattern(key, subject, transform, ctx, True)
#             for key in pattern.keys
#         ]
#         k_var = generate_name(prefix="__match_k_")
#         v_var = generate_name(prefix="__match_v_")
#         rest_dict = f"{{{k_var}: {v_var} for {k_var}, {v_var} in {subject}.items() if {k_var} not in [{', '.join(matched_keys)}]}}"
#         compare_conditions.append(f"({pattern.rest!r} := {rest_dict})")
#     combined_conditions = " and ".join(compare_conditions)
#     return combined_conditions
# elif isinstance(pattern, ast.MatchStar):
#     return "True"
# elif isinstance(pattern, ast.Constant):
#     constant_value = repr(pattern.value)
#     return constant_value if is_nested else f"{subject} == {constant_value}"
# elif isinstance(pattern, ast.Name):
#     return pattern.id
# elif isinstance(pattern, ast.MatchAs):
#     name = pattern.name or "_"
#     as_condition = (
#         transform_pattern(pattern.pattern, subject, transform, ctx, True)
#         if pattern.pattern
#         else "True"
#     )
#     return (
#         f"({name} := {subject}) and {as_condition}"
#         if pattern.pattern
#         else f"({name} := {subject})"
#     )
# elif isinstance(pattern, ast.MatchOr):
#     or_conditions = [
#         transform_pattern(p, subject, transform, ctx, True)
#         for p in pattern.patterns
#     ]
#     return (
#         f"({' or '.join(or_conditions)})"
#         if is_nested
#         else f"{subject} == ({' or '.join(or_conditions)})"
#     )
# else:
#     raise NotImplementedError(f"Pattern type {type(pattern)} not implemented")


@Handle(ast.Match)
def handle_match(node: ast.Match, transform: TransformFunc, ctx: Context):
    # uh oh
    subject = transform(node.subject)

    subject_var = generate_name(prefix="__match_subject_")

    cases = ", ".join(
        f"([{', '.join(transform(stmt) for stmt in case.body)}] if ({transform_pattern(case.pattern, subject_var, transform, ctx)}){f' and ({transform(case.guard)})' if case.guard else ''} else None)"  # TODO we don't need an if expr
        for case in node.cases
    )

    return f"[({subject_var} := {subject}), {cases}]"
    # subject = transform(node.subject)

    # def transform_case(case: ast.match_case):
    #     condition = transform_pattern(case.pattern, subject, transform, ctx)
    #     guard = f" and ({transform(case.guard)})" if case.guard else ""
    #     body = ", ".join(transform(stmt) for stmt in case.body)
    #     return f"(lambda: ({condition}{guard} and ({body})))()"

    # cases = [transform_case(case) for case in node.cases]
    # match_expression = " or ".join(cases)
    # return f"({match_expression})"

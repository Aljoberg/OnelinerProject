import ast
from utils import Context, Handle, TransformFunc, ensure_assign, generate_name


@Handle(ast.Import)
def handle_import(node: ast.Import, transform: TransformFunc, ctx: Context):
    # https://github.com/python/cpython/blob/main/Python/codegen.c#L2889
    # d = __import__("a.b.c") probably works as intended, we don't need to import the parent modules right?
    # the instructions do that - 
    #     >>> def a(): import a.b.c as d
    # ...
    # >>> dis.dis(a)
    #   1           0 RESUME                   0
    #               4 LOAD_CONST               0 (None)
    #               6 IMPORT_NAME              0 (a.b.c)
    #               8 IMPORT_FROM              1 (b)
    #              10 SWAP                     2
    #              12 POP_TOP
    #              14 IMPORT_FROM              2 (c)
    #              16 STORE_FAST               0 (d)
    #              18 POP_TOP
    #              20 RETURN_CONST             0 (None)
    # but we should be fine
    lines = []
    for alias in node.names:
        if alias.asname:
            lines.append(ensure_assign(alias.asname, f"__import__{alias.name!r}", ctx))
            # lines.append(f"({alias.asname} := __import__({alias.name!r}))")
        else:
            mod_name = alias.name.split(".")[0]
            lines.append(ensure_assign(mod_name, f"__import__({alias.name!r})", ctx))
            # lines.append(f"({mod_name} := __import__({alias.name!r}))")
    return ", ".join(lines)


@Handle(ast.ImportFrom)
def handle_import_from(node: ast.ImportFrom, transform: TransformFunc, ctx: Context):
    # https://github.com/python/cpython/blob/main/Python/codegen.c#L2946
    # it's fine, surely nothing changed from 3.12 right?
    level = node.level
    module = node.module or ""
    module = node.module or ""
    level = node.level
    import_cached_varname = generate_name(prefix="__import_")
    import_string = f"{import_cached_varname} := __import__({module!r}, globals(), locals(), [{', '.join(repr(i.name) for i in node.names)}], {level})"
    import_var = import_cached_varname
    lines = []
    for alias in node.names:
        if alias.name == "*":
            k = generate_name(prefix="__star_")
            lines.append(f"locals().update({{{k}: getattr({import_cached_varname}, {k}) for {k} in getattr({import_cached_varname}, '__all__', 0) or (i for i in {import_cached_varname}.__dict__.keys() if i[0] != '_')}})")
            # lines.append(
            #     f"globals().{{{k}: getattr({import_cached_varname}, {k}) for {k} in getattr({import_cached_varname}, '__all__', 0) or (i for i in dir({import_cached_varname}) if not i.startswith('__'))}}"
            # )
        elif alias.asname:
            lines.append(ensure_assign(alias.asname, f"{import_var}.{alias.name}", ctx))
            # lines.append(f"({alias.asname} := {import_var}.{alias.name})")
        else:
            lines.append(ensure_assign(alias.name, f"{import_var}.{alias.name}", ctx))
            # lines.append(f"({alias.name} := {import_var}.{alias.name})")
    return f"({import_string}, {', '.join(lines)})"

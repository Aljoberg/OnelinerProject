import ast


def convert_assign_to_generator_with_temp(assign_node):
    """
    Convert an ast.Assign node into a generator expression string using assignment expressions,
    utilizing the 'for' part of the generator as a temporary variable holder.
    """
    if not isinstance(assign_node, ast.Assign):
        raise ValueError("The node must be an ast.Assign.")

    targets = assign_node.targets
    value = assign_node.value

    # Function to recursively parse targets and build the assignment expressions
    def parse_target(target, expr):
        if isinstance(target, ast.Name):
            # Simple variable assignment
            return f"{target.id} := {expr}"
        elif isinstance(target, ast.Starred):
            # Handling Starred variable (e.g., *rest)
            return f"{target.value.id} := {expr}"
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
        elif isinstance(target, ast.Subscript):
            # Subscript assignment (e.g., a[i] = value)
            sub_target = ast.unparse(target.slice)
            return f"{ast.unparse(target.value)}[{sub_target}] := {expr}"
        elif isinstance(target, ast.Attribute):
            # Attribute assignment (e.g., a.b = value)
            return f"{ast.unparse(target.value)}.{target.attr} := {expr}"
        else:
            raise TypeError("Unsupported target type for assignment.")

    # Use the first target for the assignment expression in the generator
    # first_target_expression = parse_target(targets[0], "i")
    target_exprs = [parse_target(t, "i") for t in targets]

    # Create a generator expression using the first target as the temporary variable
    gen_expr_code = f"list(None for i in [{ast.unparse(value)}] if [{', '.join(target_exprs)}])"

    return gen_expr_code


# Example of how to use the function
# We will use the example: a, b, *rest = range(10)
# Please note: The function call is commented to adhere to the instructions

code_example_generator_temp = """
a = b = type("Hi", (), {"__init__": lambda self: print("hello")})
"""
assign_node_generator_temp = ast.parse(code_example_generator_temp).body[0]
print(convert_assign_to_generator_with_temp(assign_node_generator_temp))

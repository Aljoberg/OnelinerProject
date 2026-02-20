# awesome plans

- make a statement handler
- handle each statement in each file
- make a decorator like

```py
import ast
from ..main import Handle

@Handle(ast.With, ast.AsyncWith)
def with_handler(
    node: ast.With | ast.AsyncWith, # can be inferred from decorator
    transform: (node: ast.AST) -> str
):
    ...
```

### even more awesomeness

- read previous solske naloge
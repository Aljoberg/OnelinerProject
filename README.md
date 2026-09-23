# OnelinerProject

An experimental Python source transformer that uses the abstract syntax tree
(`ast`) to rewrite Python code into a oneliner.

## Quick start

Use Python **3.10 or newer**. The transformer uses the pattern-matching AST
types introduced in Python 3.10.

From the repository root, install the package in editable mode:

```sh
python -m pip install -e .
```

To convert a Python file, run:

```sh
python -m onelinerproject.main input.py -o output_code.py
```

The installed `oneliner` command accepts the same arguments. Without arguments,
it reads `test_code.py` and writes `output_code.py`. An existing output file is
overwritten only after conversion and syntax validation succeed. To run it:

```sh
python output_code.py
```

You can also use the API without reading or writing files:

```python
from onelinerproject.main import code_to_oneliner

result = code_to_oneliner('x = 3\nprint(x + 1)')
```

Use `--debug` (or `debug=True`) for descriptive generated variable names.

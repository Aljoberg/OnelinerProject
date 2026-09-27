"""Behavioral regression cases for the supported Python syntax.

Each snippet is run as ordinary Python and as the generated expression.  Keep
cases small: a failure should point to one syntax feature or interaction.
"""

import ast
import contextlib
import io
from pathlib import Path
import re
import sys
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from onelinerproject.main import code_to_oneliner
from onelinerproject.utils import stmt_handlers


CASES = {
    "empty and expressions": "pass\n1 + 2\nprint('ok')",
    "assignment and unpacking": "a, (b, c) = (1, (2, 3))\na = b = 5\nprint(a, b, c)",
    "starred assignment": "first, *middle, last = range(5)\nprint(first, middle, last)",
    "subscript and slice assignment": "a = [0, 1, 2, 3]\na[1:3] = [8, 9]\nprint(a, a[:2], a[::2])",
    "attribute assignment": "class Box: pass\nb = Box()\nb.value = 4\nprint(b.value)",
    "augmented assignments": "x = 7\nx += 2\nx *= 3\nx //= 2\nprint(x)",
    "walrus": "print((x := 3) + x)",
    "delete subscript and attribute": "class Box: pass\nb = Box()\nb.x = 1\na = [1, 2]\ndel a[0], b.x\nprint(a, hasattr(b, 'x'))",
    "annotations": "x: int = 3\ny: str\nprint(x, __annotations__)",
    "all arithmetic operators": "print(2+3, 5-2, 2**3, 3*4, 7/2, 7//2, 7%2)",
    "all bit operators": "print(1<<3, 8>>2, 5|2, 5^2, 5&3, ~2)",
    "matrix multiplication": "class M:\n def __matmul__(self, other): return 42\nprint(M() @ M())",
    "comparisons": "x = 3\nprint(x == 3, x != 4, x < 4, x <= 3, x > 2, x >= 3, x is None, x is not None, x in [2,3], x not in [4])",
    "chained comparisons": "print(1 < 2 < 3, 1 < 2 > 3)",
    "unary operators": "x = 2\nprint(+x, -x, ~x, not x, not False)",
    "boolean short circuit": "events = []\ndef mark(x):\n events.append(x)\n return x\nprint(mark(0) and mark(1), mark(2) or mark(3), events)",
    "if elif else": "x = 2\nif x < 0: print('negative')\nelif x == 2: print('two')\nelse: print('other')",
    "conditional expression": "print('yes' if 1 < 2 else 'no')",
    "for else": "for x in [1, 2]: print(x)\nelse: print('done')",
    "for break and continue": "for x in range(5):\n if x == 1: continue\n if x == 4: break\n print(x)\nelse: print('bad')",
    "nested loops": "for x in range(2):\n for y in range(3):\n  if y == 1: break\n  print(x, y)",
    "while else": "x = 0\nwhile x < 2:\n x += 1\n print(x)\nelse: print('done')",
    "while break continue": "x = 0\nwhile x < 5:\n x += 1\n if x == 2: continue\n if x == 4: break\n print(x)\nelse: print('bad')",
    "functions and defaults": "def f(x, y=3, *, z=4): return x+y+z\nprint(f(2), f(2,z=5))",
    "varargs and kwargs": "def f(*args, **kwargs): return args, kwargs\nprint(f(1,2,a=3))",
    "lambda": "f = lambda x, y=2: x + y\nprint(f(4))",
    "recursion": "def fact(n):\n if n < 2: return 1\n return n * fact(n-1)\nprint(fact(5))",
    "global": "x = 1\ndef f():\n global x\n x = 3\nf()\nprint(x)",
    "nonlocal": "def outer():\n x = 1\n def inner():\n  nonlocal x\n  x += 2\n inner()\n return x\nprint(outer())",
    "decorator": "def decorate(f):\n def wrapped(): return f() + 1\n return wrapped\n@decorate\ndef f(): return 2\nprint(f())",
    "class and methods": "class A:\n x = 3\n def get(self): return self.x\nprint(A().get())",
    "list tuple set dict": "print([1,2], (1,2), {1,2}, {'a':1})",
    "list comprehension": "print([x*x for x in range(5) if x%2])",
    "set comprehension": "print({x%3 for x in range(5)})",
    "dict comprehension": "print({x: x*x for x in range(3)})",
    "generator expression": "print(sum(x*x for x in range(4)))",
    "nested comprehension": "print([(x,y) for x in range(2) for y in range(3) if y>x])",
    "fstring conversions": "x = 'é'\nprint(f'{x!r} {x!a} {3.14159:.2f} {{ok}}')",
    "import and from import": "import math as m\nfrom collections import deque as D\nprint(m.floor(2.7), list(D([1,2])))",
    "raise exception": "try:\n raise ValueError('oops')\nexcept ValueError as e:\n print(str(e))",
    "bare raise": "try:\n raise ValueError('oops')\nexcept ValueError:\n try: raise\n except ValueError: print('reraised')",
    "assertion": "assert 2 + 2 == 4\ntry: assert False, 'bad'\nexcept AssertionError as e: print(str(e))",
    "with context manager": "from contextlib import nullcontext\nwith nullcontext(3) as x: print(x)",
    "multiple with items": "from contextlib import nullcontext\nwith nullcontext(2) as x, nullcontext(3) as y: print(x+y)",
    "try except else finally": "try:\n x = 1/1\nexcept ZeroDivisionError: print('bad')\nelse: print('else')\nfinally: print('finally')",
    "try exception handler": "try: 1/0\nexcept ZeroDivisionError as e: print(type(e).__name__)\nfinally: print('done')",
    "match literal and wildcard": "match 2:\n case 1: print('one')\n case 2: print('two')\n case _: print('other')",
    "match or guard": "match [2, 3]:\n case [1 | 2, x] if x > 2: print(x)\n case _: print('other')",
    "match mapping": "match {'kind':'point','x':2}:\n case {'kind':'point', 'x': x}: print(x)",
    "match sequence star": "match [1,2,3,4]:\n case [first,*rest]: print(first,rest)",
    "match singleton": "for x in [None, True, False]:\n match x:\n  case None: print('none')\n  case True: print('true')\n  case False: print('false')",
    "match class": "class Point:\n __match_args__ = ('x','y')\n def __init__(self,x,y): self.x,self.y=x,y\nmatch Point(2,3):\n case Point(x,y): print(x,y)",
    "yield": "def f():\n yield 1\n yield 2\nprint(list(f()))",
    "yield from": "def f():\n yield from [1,2]\nprint(list(f()))",
    "async await": "import asyncio\nasync def f(): return await asyncio.sleep(0, result=3)\nprint(asyncio.run(f()))",
    "decorator order": "events=[]\ndef mark(label):\n def decorate(f):\n  events.append(label)\n  return f\n return decorate\n@mark('outer')\n@mark('inner')\ndef f(): return 1\nprint(events)",
    "class decorator order": "events=[]\ndef mark(label):\n def decorate(cls):\n  events.append(label)\n  return cls\n return decorate\n@mark('outer')\n@mark('inner')\nclass C: pass\nprint(events)",
    "positional only arguments": "def f(x, /, y): return x+y\nprint(f(2,3))\ntry: f(x=2,y=3)\nexcept TypeError: print('positional only')",
    "unhandled exception": "try: raise TypeError('bad')\nexcept ValueError: print('wrong')\nprint('after')",
    "with exception suppression": "class C:\n def __enter__(self): return self\n def __exit__(self, *args): return True\nwith C(): raise ValueError('ignored')\nprint('after')",
    "return from for": "def f():\n for x in range(3):\n  if x == 1: return x\n return 9\nprint(f())",
    "augmented subscript evaluated once": "events=[]\ndef index():\n events.append('index')\n return 0\na=[1]\na[index()] += 2\nprint(a,events)",
    "chained comparison short circuit": "events=[]\ndef value(x):\n events.append(x)\n return x\nprint(value(3) < value(2) < value(1),events)",
    "inplace list identity": "a=[1]\nb=a\na += [2]\nprint(a,b,a is b)",
    "augmented attribute evaluated once": "events=[]\nclass C: pass\nc=C()\nc.x=1\ndef target():\n events.append('target')\n return c\ntarget().x += 2\nprint(c.x,events)",
    "keyword only rejects positional": "def f(*, x): return x\nprint(f(x=3))\ntry: f(3)\nexcept TypeError: print('keyword only')",
    "positional only defaults": "def f(x=2, /, y=3): return x+y\nprint(f(), f(4,5))",
    "lambda positional and keyword only": "f=lambda x, /, *, y=2: x+y\nprint(f(3), f(3,y=4))",
    "decorator expression evaluation": "events=[]\ndef mark(label):\n events.append('evaluate '+label)\n def dec(f):\n  events.append('apply '+label)\n  return f\n return dec\n@mark('outer')\n@mark('inner')\ndef f(): pass\nprint(events)",
    "generator send": "def f():\n x = yield 1\n yield x+1\ng=f()\nprint(next(g),g.send(3))",
    "negative and stepped slices": "a=list(range(8))\nprint(a[-4:-1],a[::-2])",
    "nested mapping pattern": "match {'a': {'b': 2}, 'c': 3}:\n case {'a': {'b': x}, **rest}: print(x, rest)",
    "match as capture": "match [1,2]:\n case [1, x] as whole: print(x,whole)",
    "match class keyword": "class C:\n def __init__(self): self.x=2\nmatch C():\n case C(x=value): print(value)",
    "try bare except": "try: raise ValueError('x')\nexcept: print('caught')",
    "try else skipped": "try: raise ValueError('x')\nexcept ValueError: print('caught')\nelse: print('bad')",
    "finally on unhandled exception": "try:\n try: raise TypeError('x')\n finally: print('finally')\nexcept TypeError: print('caught')",
    "raise from": "try:\n try: raise ValueError('root')\n except ValueError as e: raise TypeError('outer') from e\nexcept TypeError as e: print(type(e.__cause__).__name__)",
    "assert true message lazy": "def boom(): raise RuntimeError('bad')\nassert True, boom()\nprint('ok')",
    "with manager return false": "class C:\n def __enter__(self): return 1\n def __exit__(self,*args): print('exit',args[0].__name__ if args[0] else None); return False\ntry:\n with C() as value: print(value); raise ValueError('x')\nexcept ValueError: print('caught')",
    "multiple assignment rhs once": "events=[]\ndef make(): events.append('make'); return 3\na=b=make()\nprint(a,b,events)",
    "short circuit side effects": "events=[]\ndef f(x): events.append(x); return x\nprint(f(False) and f(1),f(True) or f(2),events)",
    "unicode identifiers": "café = 3\nprint(café)",
}

ASYNC_WITH = "import asyncio\nclass CM:\n async def __aenter__(self): return 3\n async def __aexit__(self, *args): return False\nasync def f():\n async with CM() as x: return x\nprint(asyncio.run(f()))"
YIELD_IN_FOR = "def f():\n for x in range(3): yield x\nprint(list(f()))"
DECORATED_NONLOCAL = "def dec(f):\n def wrapper(): return f()\n return wrapper\ndef outer():\n x=1\n @dec\n def inner():\n  nonlocal x\n  x+=1\n  return x\n return inner\nprint(outer()())"


def outcome(code):
    output = io.StringIO()
    namespace = {"__name__": "__main__"}
    error = None
    with contextlib.redirect_stdout(output):
        try:
            exec(compile(code, "<case>", "exec"), namespace)
        except BaseException as exc:
            error = (type(exc).__name__, str(exc))
    return output.getvalue(), error


class SyntaxSemanticsTests(unittest.TestCase):
    def test_every_handler_has_a_case(self):
        # Operator nodes and expressions count too; the inventory makes a new
        # handler visible as a missing test instead of silently omitting it.
        exercised = {type(node) for source in (*CASES.values(), ASYNC_WITH)
                     for node in ast.walk(ast.parse(textwrap.dedent(source)))}
        missing = {node.__name__ for node in stmt_handlers if node not in exercised}
        self.assertEqual(missing, set())

    @unittest.expectedFailure
    def test_async_with_known_failure(self):
        """Async context managers need awaited enter/exit methods."""
        self.assertEqual(outcome(code_to_oneliner(ASYNC_WITH)), outcome(ASYNC_WITH))

    @unittest.expectedFailure
    def test_yield_in_for_known_failure(self):
        """The generated list comprehension cannot contain yield."""
        self.assertEqual(outcome(code_to_oneliner(YIELD_IN_FOR)), outcome(YIELD_IN_FOR))

    @unittest.expectedFailure
    def test_decorated_nonlocal_known_failure(self):
        """A decorated function name has no direct closure cell for nonlocal."""
        self.assertEqual(outcome(code_to_oneliner(DECORATED_NONLOCAL)), outcome(DECORATED_NONLOCAL))


def make_case_test(source):
    def test(self):
        source_code = textwrap.dedent(source)
        generated = code_to_oneliner(source_code)
        self.assertNotIn("\n", generated)
        self.assertEqual(outcome(generated), outcome(source_code))
    return test


for case_name, case_source in CASES.items():
    method_name = "test_" + re.sub(r"\W+", "_", case_name).strip("_")
    setattr(SyntaxSemanticsTests, method_name, make_case_test(case_source))


if __name__ == "__main__":
    unittest.main()

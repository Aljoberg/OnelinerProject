"""Top-level await is supported by async runners such as Pyodide."""

import ast
import asyncio
import contextlib
import inspect
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from onelinerproject.main import code_to_oneliner, oneline_main


def run_async_source(source):
    code = compile(source, "<async-test>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
    output = io.StringIO()
    namespace = {}
    with contextlib.redirect_stdout(output):
        result = eval(code, namespace)
        if inspect.iscoroutine(result):
            asyncio.run(result)
    return output.getvalue()


class TopLevelAwaitTests(unittest.TestCase):
    def assert_equivalent(self, source):
        generated = code_to_oneliner(source)
        self.assertNotIn("\n", generated)
        self.assertEqual(run_async_source(generated), run_async_source(source))
        self.assertIn("await", generated)

    def test_direct_await_and_following_statement(self):
        self.assert_equivalent(
            "import asyncio\nvalue = await asyncio.sleep(0, result=3)\nprint(value + 1)"
        )

    def test_await_inside_conditional(self):
        self.assert_equivalent(
            "import asyncio\nif True:\n print(await asyncio.sleep(0, result='ready'))\nprint('done')"
        )

    def test_await_inside_for_loop(self):
        self.assert_equivalent(
            "import asyncio\nfor number in range(3):\n print(await asyncio.sleep(0, result=number))"
        )

    def test_await_inside_list_comprehension(self):
        self.assert_equivalent(
            "import asyncio\nprint([await asyncio.sleep(0, result=n) for n in range(3)])"
        )

    def test_oneline_command_accepts_await(self):
        source = "import asyncio\nprint(await asyncio.sleep(0, result=5))"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            oneline_main([source])
        self.assertEqual(run_async_source(output.getvalue()), "5\n")

    @unittest.expectedFailure
    def test_await_inside_while_known_failure(self):
        self.assert_equivalent(
            "import asyncio\nx = 0\nwhile x < 2:\n x += 1\n print(await asyncio.sleep(0, result=x))"
        )

    @unittest.expectedFailure
    def test_await_inside_try_known_failure(self):
        self.assert_equivalent(
            "import asyncio\ntry:\n print(await asyncio.sleep(0, result=1))\nexcept ValueError: pass"
        )

    @unittest.expectedFailure
    def test_await_inside_with_known_failure(self):
        self.assert_equivalent(
            "import asyncio\nfrom contextlib import nullcontext\nwith nullcontext():\n print(await asyncio.sleep(0, result=1))"
        )


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from onelinerproject.main import code_to_oneliner


class TransformerTests(unittest.TestCase):
    def assert_equivalent(self, source):
        generated = code_to_oneliner(source)
        self.assertNotIn('\n', generated)
        outputs = []
        for code in (source, generated):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(code, {})
            outputs.append(output.getvalue())
        self.assertEqual(*outputs)

    def test_statements_and_empty_input(self):
        self.assert_equivalent('x = 3\ny = 4\nprint(x + y)')
        self.assert_equivalent('')

    def test_condition_guards_entire_body(self):
        self.assert_equivalent('if False:\n print(1)\n print(2)\nprint(3)')
        self.assert_equivalent('if True:\n print(1)\n print(2)')

    def test_walrus_keeps_original_name(self):
        self.assert_equivalent('print((value := 7))\nprint(value)')

    def test_slice_assignment(self):
        self.assert_equivalent('values = [1, 2, 3, 4]\ni = 1\nvalues[i:3] = [9]\nprint(values)')

    def test_dotted_import_alias(self):
        self.assert_equivalent('import xml.etree.ElementTree as ET\nprint(ET.Element("test").tag)')

    def test_fstrings(self):
        self.assert_equivalent('value = "quote\\\" and newline\\n"\nwidth = 30\nprint(f"{{literal}} {value!r:>{width}}")')
        self.assert_equivalent('print(f"{chr(233)!a} {3.14159:.2f}")')

    def test_repeated_calls_and_failure_cleanup(self):
        source = 'x, y = [1, 2]\nprint(x, y)'
        expected = code_to_oneliner(source)
        self.assertEqual(expected, code_to_oneliner(source))
        with self.assertRaises(NotImplementedError):
            code_to_oneliner('async def f():\n return (x := 1)\n async for i in []:\n  pass')
        self.assertEqual(expected, code_to_oneliner(source))

    def test_argument_names_are_reserved(self):
        self.assert_equivalent('def f(a):\n return a + 1\nprint(f(4))')

    def test_invalid_scope(self):
        with self.assertRaises(SyntaxError):
            code_to_oneliner('return 1')

    def test_debug_names_are_valid_and_do_not_collide(self):
        source = '__temp_subscript_assignment__values_0__a = 7\nvalues = [0]\nvalues[0], x = [1, 2]\nprint(values, x, __temp_subscript_assignment__values_0__a)'
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(code_to_oneliner(source, debug=True), {})
        self.assertEqual(output.getvalue(), '[1] 2 7\n')

    def test_cli_and_import_have_no_side_effects(self):
        env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
        with tempfile.TemporaryDirectory() as directory:
            imported = subprocess.run([sys.executable, '-c', 'import onelinerproject.main'], cwd=directory, env=env, capture_output=True, text=True)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertEqual(imported.stdout, '')
            self.assertEqual(list(Path(directory).iterdir()), [])
            source = Path(directory) / 'input.py'
            target = Path(directory) / 'result.py'
            source.write_text('print("hello")', encoding='utf-8')
            command = [sys.executable, '-m', 'onelinerproject.main', str(source), '-o', str(target)]
            converted = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(converted.returncode, 0, converted.stderr)
            result = subprocess.run([sys.executable, str(target)], capture_output=True, text=True)
            self.assertEqual(result.stdout, 'hello\n')
            source.write_text('return 1', encoding='utf-8')
            failed = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn('hello', target.read_text())
            same_file = subprocess.run(command[:-1] + [str(source)], env=env, capture_output=True, text=True)
            self.assertNotEqual(same_file.returncode, 0)
            self.assertEqual(source.read_text(), 'return 1')


if __name__ == '__main__':
    unittest.main()

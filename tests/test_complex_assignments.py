"""Evaluation order, unpacking, deletion, and annotation regressions."""

import contextlib
import io
from pathlib import Path
import re
import sys
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from onelinerproject.main import code_to_oneliner


CASES = {
    "subscript store evaluation order": """
        events = []
        class Box:
            def __setitem__(self, key, value): events.append(('set', key, value))
        box = Box()
        def target(): events.append('target'); return box
        def index(): events.append('index'); return 0
        def rhs(): events.append('rhs'); return 4
        target()[index()] = rhs()
        print(events)
    """,
    "attribute store evaluation order": """
        events = []
        class Box:
            def __setattr__(self, name, value): events.append(('set', name, value))
        box = Box()
        def target(): events.append('target'); return box
        def rhs(): events.append('rhs'); return 4
        target().value = rhs()
        print(events)
    """,
    "subscript store special lookup": """
        events = []
        class Box:
            def __setitem__(self, key, value): events.append(('class', key, value))
        box = Box()
        box.__setitem__ = lambda key, value: events.append(('instance', key, value))
        box[0] = 4
        print(events)
    """,
    "rhs failure skips subscript target": """
        events = []
        class Box:
            def __setitem__(self, key, value): events.append('set')
        box = Box()
        def target(): events.append('target'); return box
        def index(): events.append('index'); return 0
        def rhs(): events.append('rhs'); raise ValueError('stop')
        try: target()[index()] = rhs()
        except ValueError: print(events)
    """,
    "rhs failure skips attribute target": """
        events = []
        class Box:
            def __setattr__(self, key, value): events.append('set')
        box = Box()
        def target(): events.append('target'); return box
        def rhs(): events.append('rhs'); raise ValueError('stop')
        try: target().field = rhs()
        except ValueError: print(events)
    """,
    "chained stores left to right": """
        events = []
        class Box:
            def __setitem__(self, key, value): events.append(('set', key, value))
        box = Box()
        def target(label): events.append(('target', label)); return box
        def rhs(): events.append('rhs'); return 7
        target('first')[0] = target('second')[1] = rhs()
        print(events)
    """,
    "chained target failure stops later targets": """
        events = []
        class Box:
            def __setitem__(self, key, value):
                events.append(('set', key))
                if key == 0: raise ValueError('stop')
        box = Box()
        def rhs(): events.append('rhs'); return 7
        try: box[0] = box[1] = rhs()
        except ValueError: print(events)
    """,
    "chained name attribute and subscript": """
        events = []
        class Box:
            def __setattr__(self, name, value): events.append(('attr', name, value))
            def __setitem__(self, key, value): events.append(('item', key, value))
        box = Box()
        def rhs(): events.append('rhs'); return 3
        value = box.field = box[0] = rhs()
        print(value, events)
    """,
    "unpacking from generator": """
        events = []
        def values():
            events.append(1)
            yield 1
            events.append(2)
            yield 2
            events.append(3)
            yield 3
        a, b, c = values()
        print(a, b, c, events)
    """,
    "nested unpacking": """
        (a, [b, c]), d = ((1, [2, 3]), 4)
        print(a, b, c, d)
    """,
    "starred unpacking from generator": """
        a, *middle, z = (x for x in range(5))
        print(a, middle, z)
    """,
    "unpack into subscript and attribute": """
        events = []
        class Box:
            def __setattr__(self, name, value): events.append(('attr', name, value))
            def __setitem__(self, key, value): events.append(('item', key, value))
        box = Box()
        def target(): events.append('target'); return box
        target()[0], target().value = (1, 2)
        print(events)
    """,
    "unpack store order": """
        events = []
        class Box:
            def __setitem__(self, key, value): events.append(('set', key, value))
        box = Box()
        def index(label): events.append(('index', label)); return label
        box[index('a')], box[index('b')] = (1, 2)
        print(events)
    """,
    "unpack too few": """
        try:
            a, b = [1]
        except ValueError as error:
            print(type(error).__name__, 'a' in globals())
    """,
    "unpack too many": """
        try:
            a, b = [1, 2, 3]
        except ValueError as error:
            print(type(error).__name__, 'a' in globals())
    """,
    "chained unpack and name": """
        events = []
        def rhs(): events.append('rhs'); return [1, 2]
        (a, b) = whole = rhs()
        print(a, b, whole, events)
    """,
    "walrus in assignment rhs": """
        a = (b := 3) + 4
        print(a, b)
    """,
    "delete subscript special lookup": """
        events = []
        class Box:
            def __delitem__(self, key): events.append(('class', key))
        box = Box()
        box.__delitem__ = lambda key: events.append(('instance', key))
        del box[0]
        print(events)
    """,
    "delete targets left to right": """
        events = []
        class Box:
            def __delitem__(self, key): events.append(('item', key))
            def __delattr__(self, name): events.append(('attr', name))
        box = Box()
        del box[0], box.value
        print(events)
    """,
    "delete subscript slice": """
        items = [1, 2, 3, 4, 5]
        del items[1:4:2]
        print(items)
    """,
    "delete module name": """
        value = 3
        del value
        print('value' in globals())
    """,
    "delete target failure stops later targets": """
        events = []
        class Box:
            def __delitem__(self, key):
                events.append(key)
                if key == 0: raise ValueError('stop')
        box = Box()
        try: del box[0], box[1]
        except ValueError: print(events)
    """,
    "annotation with value": """
        events = []
        def annotation(): events.append('annotation'); return int
        def rhs(): events.append('rhs'); return 3
        x: annotation() = rhs()
        print(x, events, __annotations__['x'] is int)
    """,
    "class annotation with value": """
        events = []
        def annotation(): events.append('annotation'); return int
        def rhs(): events.append('rhs'); return 3
        class Box:
            x: annotation() = rhs()
        print(Box.x, events, Box.__annotations__['x'] is int)
    """,
    "annotation without value": """
        events = []
        def annotation(): events.append('annotation'); return int
        x: annotation()
        print(events, 'x' in globals(), __annotations__['x'] is int)
    """,
}

LOCAL_DELETE = """
def f():
    x = 3
    del x
    try: print(x)
    except UnboundLocalError: print('unbound')
f()
"""


def outcome(source):
    output = io.StringIO()
    error = None
    with contextlib.redirect_stdout(output):
        try:
            exec(compile(source, "<assignment-test>", "exec"), {})
        except BaseException as exc:
            error = type(exc).__name__, str(exc)
    return output.getvalue(), error


class ComplexAssignmentTests(unittest.TestCase):
    @unittest.expectedFailure
    def test_local_deletion_known_failure(self):
        source = textwrap.dedent(LOCAL_DELETE)
        self.assertEqual(outcome(code_to_oneliner(source)), outcome(source))


def make_test(source):
    def test(self):
        source_code = textwrap.dedent(source)
        generated = code_to_oneliner(source_code)
        self.assertNotIn("\n", generated)
        self.assertEqual(outcome(generated), outcome(source_code), generated)
    return test


for name, source in CASES.items():
    setattr(ComplexAssignmentTests, "test_" + re.sub(r"\W+", "_", name), make_test(source))


if __name__ == "__main__":
    unittest.main()

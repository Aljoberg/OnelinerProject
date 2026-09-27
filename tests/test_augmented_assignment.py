"""Detailed evaluation-order and data-model tests for augmented targets."""

import contextlib
import io
from pathlib import Path
import sys
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from onelinerproject.main import code_to_oneliner


def run(source):
    output = io.StringIO()
    error = None
    with contextlib.redirect_stdout(output):
        try:
            exec(compile(source, "<augmented-test>", "exec"), {})
        except BaseException as exc:
            error = (type(exc).__name__, str(exc))
    return output.getvalue(), error


class AugmentedAssignmentTests(unittest.TestCase):
    def assert_equivalent(self, source):
        source = textwrap.dedent(source)
        generated = code_to_oneliner(source)
        self.assertNotIn("\n", generated)
        self.assertEqual(run(generated), run(source), generated)

    def test_all_numeric_operators_on_subscripts_and_attributes(self):
        for operator in ("+", "-", "*", "/", "//", "%", "**", "<<", ">>", "&", "|", "^"):
            for target in ("items[0]", "box.value"):
                with self.subTest(operator=operator, target=target):
                    self.assert_equivalent(f"""
                        class Box: pass
                        box = Box()
                        box.value = 8
                        items = [8]
                        {target} {operator}= 2
                        print(items[0], box.value)
                    """)

    def test_subscript_evaluation_order_and_inplace_method(self):
        self.assert_equivalent("""
            events = []
            class Value:
                def __iadd__(self, other):
                    events.append(('iadd', other))
                    return self
            class Container:
                def __getitem__(self, key):
                    events.append(('get', key))
                    return value
                def __setitem__(self, key, item):
                    events.append(('set', key, item is value))
            value = Value()
            container = Container()
            def target():
                events.append('target')
                return container
            def index():
                events.append('index')
                return 3
            def rhs():
                events.append('rhs')
                return 5
            target()[index()] += rhs()
            print(events)
        """)

    def test_attribute_evaluation_order_and_descriptor(self):
        self.assert_equivalent("""
            events = []
            class Value:
                def __iadd__(self, other):
                    events.append(('iadd', other))
                    return self
            value = Value()
            class Box:
                @property
                def field(self):
                    events.append('get')
                    return value
                @field.setter
                def field(self, new):
                    events.append(('set', new is value))
            box = Box()
            def target():
                events.append('target')
                return box
            def rhs():
                events.append('rhs')
                return 5
            target().field += rhs()
            print(events)
        """)

    def test_inplace_identity_for_mutable_values(self):
        for target in ("items[0]", "box.value"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    class Box: pass
                    box = Box()
                    box.value = [1]
                    items = [[1]]
                    alias = {target}
                    {target} += [2]
                    print({target}, alias, {target} is alias)
                """)

    def test_nested_subscript_target(self):
        self.assert_equivalent("""
            events = []
            class Box: pass
            box = Box()
            box.items = [10]
            def outer():
                events.append('outer')
                return box
            def index():
                events.append('index')
                return 0
            outer().items[index()] += 4
            print(box.items, events)
        """)

    def test_nested_attribute_target(self):
        self.assert_equivalent("""
            events = []
            class Box: pass
            box = Box()
            box.child = Box()
            box.child.value = 10
            def outer():
                events.append('outer')
                return box
            outer().child.value += 4
            print(box.child.value, events)
        """)

    def test_slice_subscript_target(self):
        self.assert_equivalent("""
            events = []
            class Items(list):
                def __getitem__(self, key):
                    events.append(('get', key.start, key.stop, key.step))
                    return list.__getitem__(self, key)
                def __setitem__(self, key, value):
                    events.append(('set', key.start, key.stop, key.step))
                    return list.__setitem__(self, key, value)
            items = Items([1, 2, 3, 4])
            items[1:3] += [9]
            print(items, events)
        """)

    def test_rhs_failure_skips_inplace_and_store(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    class Value:
                        def __iadd__(self, other):
                            events.append('iadd')
                            return self
                    value = Value()
                    class Container:
                        def __getitem__(self, key):
                            events.append('get')
                            return value
                        def __setitem__(self, key, item):
                            events.append('set')
                    class Box:
                        @property
                        def field(self):
                            events.append('get')
                            return value
                        @field.setter
                        def field(self, item):
                            events.append('set')
                    container = Container()
                    box = Box()
                    def rhs():
                        events.append('rhs')
                        raise ValueError('stop')
                    try:
                        {target} += rhs()
                    except ValueError:
                        print(events)
                """)

    def test_inplace_failure_skips_store(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    class Value:
                        def __iadd__(self, other):
                            events.append('iadd')
                            raise ValueError('stop')
                    value = Value()
                    class Container:
                        def __getitem__(self, key): return value
                        def __setitem__(self, key, item): events.append('set')
                    class Box:
                        @property
                        def field(self): return value
                        @field.setter
                        def field(self, item): events.append('set')
                    container = Container()
                    box = Box()
                    try:
                        {target} += 1
                    except ValueError:
                        print(events)
                """)

    def test_subscript_key_failure_skips_get_and_rhs(self):
        self.assert_equivalent("""
            events = []
            class Container:
                def __getitem__(self, key): events.append('get'); return 1
                def __setitem__(self, key, value): events.append('set')
            container = Container()
            def target(): events.append('target'); return container
            def index(): events.append('index'); raise ValueError('key')
            def rhs(): events.append('rhs'); return 2
            try: target()[index()] += rhs()
            except ValueError: print(events)
        """)

    def test_read_failure_skips_rhs_and_store(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    class Container:
                        def __getitem__(self, key):
                            events.append('get')
                            raise ValueError('read')
                        def __setitem__(self, key, value): events.append('set')
                    class Box:
                        @property
                        def field(self):
                            events.append('get')
                            raise ValueError('read')
                        @field.setter
                        def field(self, value): events.append('set')
                    container = Container()
                    box = Box()
                    def rhs(): events.append('rhs'); return 2
                    try: {target} += rhs()
                    except ValueError: print(events)
                """)

    def test_store_failure_occurs_after_inplace_mutation(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    value = [1]
                    class Container:
                        def __getitem__(self, key): events.append('get'); return value
                        def __setitem__(self, key, item):
                            events.append('set')
                            raise ValueError('store')
                    class Box:
                        @property
                        def field(self): events.append('get'); return value
                        @field.setter
                        def field(self, item):
                            events.append('set')
                            raise ValueError('store')
                    container = Container()
                    box = Box()
                    try: {target} += [2]
                    except ValueError: print(value, events)
                """)

    def test_inplace_method_can_return_replacement_value(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    class Value:
                        def __iadd__(self, other):
                            events.append('iadd')
                            return other + 10
                    old = Value()
                    class Container:
                        def __init__(self): self.value = old
                        def __getitem__(self, key): return self.value
                        def __setitem__(self, key, value): self.value = value
                    class Box:
                        def __init__(self): self.value = old
                        @property
                        def field(self): return self.value
                        @field.setter
                        def field(self, value): self.value = value
                    container = Container()
                    box = Box()
                    {target} += 2
                    print(container.value == 12, box.value == 12, events)
                """)

    def test_matrix_inplace_method(self):
        for target in ("container[0]", "box.field"):
            with self.subTest(target=target):
                self.assert_equivalent(f"""
                    events = []
                    class Value:
                        def __imatmul__(self, other):
                            events.append(('imatmul', other))
                            return self
                    value = Value()
                    class Container:
                        def __getitem__(self, key): return value
                        def __setitem__(self, key, item): events.append(item is value)
                    class Box:
                        @property
                        def field(self): return value
                        @field.setter
                        def field(self, item): events.append(item is value)
                    container = Container()
                    box = Box()
                    {target} @= 3
                    print(events)
                """)

    def test_subscript_store_uses_special_method_lookup(self):
        self.assert_equivalent("""
            events = []
            class Container:
                def __init__(self): self.value = 1
                def __getitem__(self, key): return self.value
                def __setitem__(self, key, value):
                    events.append('class method')
                    self.value = value
            container = Container()
            container.__setitem__ = lambda key, value: events.append('instance attribute')
            container[0] += 2
            print(container.value, events)
        """)


if __name__ == "__main__":
    unittest.main()

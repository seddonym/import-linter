from contextlib import contextmanager

import pytest
from importlinter.domain.imports import DirectImport, ImportExpression, Module


@contextmanager
def does_not_raise():
    yield


class TestModule:
    def test_object_representation(self):
        test_object = Module("new_module")
        assert repr(test_object) == "<Module: new_module>"

    @pytest.mark.parametrize(
        ("first_object", "second_object", "expected_bool"),
        [
            (Module("first"), Module("second"), False),
            (Module("same"), Module("same"), True),
            (Module("different"), "different", False),
        ],
    )
    def test_equal_magic_method(self, first_object, second_object, expected_bool):
        comparison_result = first_object == second_object
        assert comparison_result is expected_bool

    @pytest.mark.parametrize(
        ("module", "expected_parent", "exception"),
        [
            (Module("parent.child"), Module("parent"), does_not_raise()),
            (Module("child"), Module(""), pytest.raises(ValueError)),
        ],
    )
    def test_parent(self, module, expected_parent, exception):
        with exception:
            assert module.parent == expected_parent

    @pytest.mark.parametrize(
        ("child", "parent", "expected_bool"),
        [
            (Module("parent.child"), Module("parent"), True),
            (Module("grandparent.parent.child"), Module("grandparent"), False),
            (Module("first_child"), Module("second_child"), False),
        ],
    )
    def test_is_child_of(self, child, parent, expected_bool):
        assert child.is_child_of(parent) is expected_bool


class TestDirectImport:
    def test_object_representation(self):
        test_object = DirectImport(
            importer=Module("mypackage.foo"),
            imported=Module("mypackage.bar"),
        )
        assert repr(test_object) == "<DirectImport: mypackage.foo -> mypackage.bar>"

    @pytest.mark.parametrize(
        ("test_object", "expected_string"),
        [
            (
                DirectImport(importer=Module("mypackage.foo"), imported=Module("mypackage.bar")),
                "mypackage.foo -> mypackage.bar",
            ),
            (
                DirectImport(
                    importer=Module("mypackage.foo"),
                    imported=Module("mypackage.bar"),
                    line_number=10,
                ),
                "mypackage.foo -> mypackage.bar (l. 10)",
            ),
        ],
    )
    def test_string_object_representation(self, test_object, expected_string):
        assert str(test_object) == expected_string


class TestImportExpression:
    def test_object_representation(self):
        test_object = ImportExpression(
            importer="mypackage.foo",
            imported="mypackage.bar"
        )
        assert repr(test_object) == "<ImportExpression: mypackage.foo -> mypackage.bar>"

    def test_string_object_representation(self):
        expression = ImportExpression(importer="mypackage.foo", imported="mypackage.bar")
        assert str(expression) == "mypackage.foo -> mypackage.bar"

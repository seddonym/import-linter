from contextlib import contextmanager

import pytest

from importlinter.domain.imports import (
    DirectImport,
    ImportExpression,
    Module,
    ModuleExpression,
)


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

    @pytest.mark.parametrize(
        ("candidate", "package", "expected_bool"),
        [
            (Module("somepackage"), Module("somepackage"), True),
            (Module("somepackage.foo"), Module("somepackage"), True),
            (Module("somepackage.foo.blue"), Module("somepackage"), True),
            (Module("somepackage.foo.blue"), Module("somepackage.foo"), True),
            (
                Module("somepackage.foo.blue.one.alpha"),
                Module("somepackage.foo.blue"),
                True,
            ),
            (Module("somepackage"), Module("somepackage.foo"), False),
            (Module("somepackage"), Module("differentpackage"), False),
            (Module("somepackage.foo"), Module("differentpackage"), False),
            (
                Module("somepackage.foo.blue.one.alpha"),
                Module("somepackage.foo.green"),
                False,
            ),
        ],
    )
    def test_is_in_package(self, candidate, package, expected_bool):
        assert candidate.is_in_package(package) is expected_bool


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


class TestModuleExpression:
    def test_object_representation(self):
        expression = ModuleExpression("mypackage.foo.**")
        assert repr(expression) == "<ModuleExpression: mypackage.foo.**>"


class TestImportExpression:
    def test_object_representation(self):
        test_object = ImportExpression(
            importer=ModuleExpression("mypackage.foo"),
            imported=ModuleExpression("mypackage.bar"),
        )
        assert repr(test_object) == "<ImportExpression: mypackage.foo -> mypackage.bar>"

    def test_string_object_representation(self):
        expression = ImportExpression(
            importer=ModuleExpression("mypackage.foo"),
            imported=ModuleExpression("mypackage.bar"),
        )
        assert str(expression) == "mypackage.foo -> mypackage.bar"

    @pytest.mark.parametrize(
        "first, second, expected",
        [
            (
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                True,
            ),
            (
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                ImportExpression(
                    importer=ModuleExpression("mypackage.bar"),
                    imported=ModuleExpression("mypackage.foo"),
                ),
                False,
            ),
            (
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.foobar"),
                ),
                False,
            ),
            (
                ImportExpression(
                    importer=ModuleExpression("mypackage.foo"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                ImportExpression(
                    importer=ModuleExpression("mypackage.foobar"),
                    imported=ModuleExpression("mypackage.bar"),
                ),
                False,
            ),
        ],
    )
    def test_equality(self, first, second, expected):
        assert expected == (first == second)

    @pytest.mark.parametrize(
        "importer, imported, has_wildcard_expression",
        [
            ("mypackage.foo", "mypackage.bar", False),
            ("mypackage.*", "mypackage.bar", True),
            ("mypackage.foo", "mypackage.*", True),
            ("mypackage.*", "mypackage.*", True),
            ("mypackage.*.foo", "mypackage.*.bar", True),
            ("mypackage.**", "mypackage.bar", True),
            ("mypackage.foo", "mypackage.**", True),
            ("mypackage.**", "mypackage.**", True),
            ("mypackage.**.foo", "mypackage.**.bar", True),
        ],
    )
    def test_has_wildcard_expression(self, importer, imported, has_wildcard_expression):
        expression = ImportExpression(
            importer=ModuleExpression(importer), imported=ModuleExpression(imported)
        )
        assert expression.has_wildcard_expression() == has_wildcard_expression

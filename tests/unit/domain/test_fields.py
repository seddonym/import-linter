import enum

import re
from typing import Any

import pytest

from importlinter.domain.fields import (
    BooleanField,
    IntegerField,
    EnumField,
    Field,
    ImportExpressionField,
    ListField,
    ModuleField,
    SetField,
    StringField,
    ValidationError,
)
from importlinter.domain.imports import ImportExpression, Module, ModuleExpression


def test_field_cannot_be_instantiated_with_default_and_required():
    class SomeField(Field):
        def parse(self, raw_data: str | list) -> str:
            raise NotImplementedError

    with pytest.raises(ValueError, match="A required field cannot also provide a default value."):
        SomeField(required=True, default="something")


class BaseFieldTest:
    field_class: type[Field] | None = None
    field_kwargs: dict[str, Any] = {}

    def test_field(self, raw_data, expected_value):
        field = self.field_class(**self.field_kwargs)

        if isinstance(expected_value, Exception):
            with pytest.raises(expected_value.__class__, match=re.escape(expected_value.message)):
                field.parse(raw_data) == expected_value
        else:
            assert field.parse(raw_data) == expected_value


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        ("Hello, world!", "Hello, world!"),
        (
            ["one", "two", "three"],
            ValidationError("Expected a single value, got multiple values."),
        ),
    ),
)
class TestStringField(BaseFieldTest):
    field_class = StringField


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        ("true", True),
        ("fAlSe", False),
        ("bananas", ValidationError("Could not parse a boolean from 'bananas'.")),
        (
            ["one", "two", "three"],
            ValidationError("Expected a single value, got multiple values."),
        ),
    ),
)
class TestBooleanField(BaseFieldTest):
    field_class = BooleanField


class TestIntegerField(BaseFieldTest):
    @pytest.mark.parametrize(
        "raw_data, minimum, expected_value",
        (
            ("1", None, 1),
            ("0", None, 0),
            ("-1", None, -1),
            ("44", 45, ValidationError("Must be >= 45.")),
            ("45", 45, 45),
            ("46", 45, 46),
            ("3.141", None, ValidationError("'3.141' is not an integer.")),
            ("bananas", None, ValidationError("'bananas' is not an integer.")),
            (
                ["1", "2", "3"],
                None,
                ValidationError("Expected a single value, got multiple values."),
            ),
        ),
    )
    def test_field(self, raw_data, minimum, expected_value):
        if minimum is None:
            field = IntegerField()
        else:
            field = IntegerField(minimum=minimum)

        if isinstance(expected_value, Exception):
            with pytest.raises(expected_value.__class__, match=re.escape(expected_value.message)):
                field.parse(raw_data)
        else:
            assert field.parse(raw_data) == expected_value


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        ("mypackage.foo.bar", Module("mypackage.foo.bar")),
        (
            ["one", "two", "three"],
            ValidationError("Expected a single value, got multiple values."),
        ),
        # TODO - test that it belongs in the root package.
    ),
)
class TestModuleField(BaseFieldTest):
    field_class = ModuleField


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (
            "mypackage.foo -> mypackage.bar",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo"),
                imported=ModuleExpression("mypackage.bar"),
            ),
        ),
        (
            "my_package.foo   ->   my_package.bar",  # Extra whitespaces are supported.
            ImportExpression(
                importer=ModuleExpression("my_package.foo"),
                imported=ModuleExpression("my_package.bar"),
            ),
        ),
        (
            "my_package.foo -> my_package.foo_bar",  # Underscores are supported.
            ImportExpression(
                importer=ModuleExpression("my_package.foo"),
                imported=ModuleExpression("my_package.foo_bar"),
            ),
        ),
        # Wildcards
        # ---------
        (
            "mypackage.foo.* -> mypackage.bar",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo.*"),
                imported=ModuleExpression("mypackage.bar"),
            ),
        ),
        (
            "mypackage.foo.*.baz -> mypackage.bar",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo.*.baz"),
                imported=ModuleExpression("mypackage.bar"),
            ),
        ),
        (
            "mypackage.foo -> mypackage.bar.*",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo"),
                imported=ModuleExpression("mypackage.bar.*"),
            ),
        ),
        (
            "*.*.* -> mypackage.*.foo.*",
            ImportExpression(
                importer=ModuleExpression("*.*.*"),
                imported=ModuleExpression("mypackage.*.foo.*"),
            ),
        ),
        (
            "mypackage.foo.** -> mypackage.bar",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo.**"),
                imported=ModuleExpression("mypackage.bar"),
            ),
        ),
        (
            "mypackage.foo.**.baz -> mypackage.bar",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo.**.baz"),
                imported=ModuleExpression("mypackage.bar"),
            ),
        ),
        (
            "mypackage.foo -> mypackage.bar.**",
            ImportExpression(
                importer=ModuleExpression("mypackage.foo"),
                imported=ModuleExpression("mypackage.bar.**"),
            ),
        ),
        (
            "** -> mypackage.**.foo.*",
            ImportExpression(
                importer=ModuleExpression("**"),
                imported=ModuleExpression("mypackage.**.foo.*"),
            ),
        ),
        # Invalid expressions
        # -------------------
        (
            ["one", "two", "three"],
            ValidationError("Expected a single value, got multiple values."),
        ),
        (
            "mypackage.foo - mypackage.bar",
            ValidationError('Must be in the form "package.importer -> package.imported".'),
        ),
        (
            "mypackage.foo.bar* -> mypackage.bar",
            ValidationError("A wildcard can only replace a whole module."),
        ),
        (
            "mypackage.foo.b*z -> mypackage.bar",
            ValidationError("A wildcard can only replace a whole module."),
        ),
        (
            "mypackage.foo.bar** -> mypackage.bar",
            ValidationError("A wildcard can only replace a whole module."),
        ),
        (
            "mypackage.**.*.foo -> mypackage.bar",
            ValidationError("A recursive wildcard cannot be followed by a wildcard."),
        ),
        (
            "mypackage.**.**.foo -> mypackage.bar",
            ValidationError("A recursive wildcard cannot be followed by a wildcard."),
        ),
        (
            "mypackage.*.**.foo -> mypackage.bar",
            ValidationError("A wildcard cannot be followed by a recursive wildcard."),
        ),
        (
            "mypackage.foo.b**z -> mypackage.bar",
            ValidationError("A wildcard can only replace a whole module."),
        ),
    ),
)
class TestImportExpressionField(BaseFieldTest):
    field_class = ImportExpressionField


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (
            ["mypackage.foo", "mypackage.bar"],
            [Module("mypackage.foo"), Module("mypackage.bar")],
        ),
        (
            ["mypackage.foo", "mypackage.foo"],
            [Module("mypackage.foo"), Module("mypackage.foo")],
        ),
        (["mypackage.foo", "    "], [Module("mypackage.foo")]),
        ("singlevalue", [Module("singlevalue")]),
    ),
)
class TestListField(BaseFieldTest):
    field_class = ListField
    field_kwargs = dict(subfield=ModuleField())


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (
            ["mypackage.foo", "mypackage.bar"],
            {Module("mypackage.foo"), Module("mypackage.bar")},
        ),
        (["mypackage.foo", "mypackage.foo"], {Module("mypackage.foo")}),
        (["mypackage.foo", "    "], {Module("mypackage.foo")}),
        ("singlevalue", {Module("singlevalue")}),
    ),
)
class TestSetField(BaseFieldTest):
    field_class = SetField
    field_kwargs = dict(subfield=ModuleField())


class MyEnum(enum.Enum):
    RED = "red"
    GREEN = "green"
    blue = "blue"
    NONMATCHING_ORANGE = "orange"


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        # Values:
        ("", MyEnum.RED),
        ("green", MyEnum.GREEN),
        # Lowercase attributes:
        ("blue", MyEnum.blue),
        # Values that don't match attributes:
        ("orange", MyEnum.NONMATCHING_ORANGE),
        # Trailing/leading spaces:
        (" ", MyEnum.RED),
        ("  green  ", MyEnum.GREEN),
        # Invalid choices:
        (
            "yellow",
            ValidationError(
                "Invalid value 'yellow': expected 'red', 'green', 'blue' or 'orange'."
            ),
        ),
        # Case sensitive:
        (
            "GREEN",
            ValidationError("Invalid value 'GREEN': expected 'red', 'green', 'blue' or 'orange'."),
        ),
    ),
)
class TestEnumField(BaseFieldTest):
    field_class = EnumField
    field_kwargs = dict(enum=MyEnum, default=MyEnum.RED)


class TestEnumFieldExtras:
    """
    Extra tests for the EnumField.
    """

    def test_works_with_no_default_provided(self):
        assert EnumField(MyEnum).parse("green") == MyEnum.GREEN

    @pytest.mark.parametrize("required", (True, False))
    def test_required_attribute_is_set_when_provided(self, required):
        assert EnumField(MyEnum, required=required).required is required

    def test_required_attribute_is_true_by_default(self):
        assert EnumField(MyEnum).required is True

    def test_validation_message_for_two_value_enum(self):
        class TwoValueEnum(enum.Enum):
            GREEN = "green"
            BLUE = "blue"

        with pytest.raises(
            ValidationError, match="Invalid value 'purple': expected 'green' or 'blue'."
        ):
            EnumField(TwoValueEnum).parse("purple")

    def test_requires_string_members(self):
        class InvalidEnum(enum.Enum):
            GREEN = "green"
            BLUE = 2

        with pytest.raises(
            TypeError,
            match="Unsupported Enum for EnumField: member values must all be strings.",
        ):
            EnumField(InvalidEnum)

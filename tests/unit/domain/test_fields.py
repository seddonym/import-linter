import enum
from typing import Any, Dict, Optional, Type

import pytest

from importlinter.domain.fields import (
    EnumField,
    Field,
    ImportExpressionField,
    ListField,
    ModuleField,
    SetField,
    StringField,
    ValidationError,
)
from importlinter.domain.imports import ImportExpression, Module


@enum.unique
class MyEnum(enum.Enum):
    NONE = "none"
    ONE = "one"
    TWO = "two"


class BaseFieldTest:
    field_class: Optional[Type[Field]] = None
    field_kwargs: Dict[str, Any] = {}

    def test_field(self, raw_data, expected_value):
        field = self.field_class(**self.field_kwargs)

        if isinstance(expected_value, ValidationError):
            try:
                field.parse(raw_data) == expected_value
            except ValidationError as e:
                assert e.message == expected_value.message
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
            ImportExpression(importer="mypackage.foo", imported="mypackage.bar"),
        ),
        (
            "my_package.foo -> my_package.foo_bar",  # Underscores are supported.
            ImportExpression(importer="my_package.foo", imported="my_package.foo_bar"),
        ),
        # Wildcards
        # ---------
        (
            "mypackage.foo.* -> mypackage.bar",
            ImportExpression(importer="mypackage.foo.*", imported="mypackage.bar"),
        ),
        (
            "mypackage.foo.*.baz -> mypackage.bar",
            ImportExpression(importer="mypackage.foo.*.baz", imported="mypackage.bar"),
        ),
        (
            "mypackage.foo -> mypackage.bar.*",
            ImportExpression(importer="mypackage.foo", imported="mypackage.bar.*"),
        ),
        (
            "*.*.* -> mypackage.*.foo.*",
            ImportExpression(importer="*.*.*", imported="mypackage.*.foo.*"),
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
            "mypackage.**.bar -> mypackage.baz",
            ValidationError("A wildcard can only replace a whole module."),
        ),
        (
            "*.*.* -> mypackage.*.foo.*",
            ImportExpression(importer="*.*.*", imported="mypackage.*.foo.*"),
        ),
    ),
)
class TestImportExpressionField(BaseFieldTest):
    field_class = ImportExpressionField


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (["mypackage.foo", "mypackage.bar"], [Module("mypackage.foo"), Module("mypackage.bar")]),
        (["mypackage.foo", "mypackage.foo"], [Module("mypackage.foo"), Module("mypackage.foo")]),
        ("singlevalue", [Module("singlevalue")]),
    ),
)
class TestListField(BaseFieldTest):
    field_class = ListField
    field_kwargs = dict(subfield=ModuleField())


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (["mypackage.foo", "mypackage.bar"], {Module("mypackage.foo"), Module("mypackage.bar")}),
        (["mypackage.foo", "mypackage.foo"], {Module("mypackage.foo")}),
        ("singlevalue", {Module("singlevalue")}),
    ),
)
class TestSetField(BaseFieldTest):
    field_class = SetField
    field_kwargs = dict(subfield=ModuleField())


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        # values
        (None, MyEnum.NONE),
        ("", MyEnum.NONE),
        ("one", MyEnum.ONE),
        ("two", MyEnum.TWO),
        # upper/lower cases
        ("One", MyEnum.ONE),
        ("ONE", MyEnum.ONE),
        # trailing/leading spaces
        (" ", MyEnum.NONE),
        (" one ", MyEnum.ONE),
        # exceptions
        ("three", ValidationError("Invalid value `three` must be one of ['none', 'one', 'two']")),
    ),
)
class TestEnumField(BaseFieldTest):
    field_class = EnumField
    field_kwargs = dict(enum=MyEnum, default=MyEnum.NONE)

from typing import Any, Dict, Optional, Type

import pytest

from importlinter.domain.fields import (
    DirectImportField,
    Field,
    ListField,
    ModuleField,
    StringField,
    ValidationError,
)
from importlinter.domain.imports import DirectImport, Module


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
            DirectImport(importer=Module("mypackage.foo"), imported=Module("mypackage.bar")),
        ),
        (
            ["one", "two", "three"],
            ValidationError("Expected a single value, got multiple values."),
        ),
        (
            "mypackage.foo - mypackage.bar",
            ValidationError('Must be in the form "package.importer -> package.imported".'),
        ),
    ),
)
class TestDirectImportField(BaseFieldTest):
    field_class = DirectImportField


@pytest.mark.parametrize(
    "raw_data, expected_value",
    (
        (["mypackage.foo", "mypackage.bar"], [Module("mypackage.foo"), Module("mypackage.bar")]),
        ("singlevalue", [Module("singlevalue")]),
    ),
)
class TestListField(BaseFieldTest):
    field_class = ListField
    field_kwargs = dict(subfield=ModuleField())

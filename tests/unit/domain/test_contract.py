import pytest

from importlinter.domain.contract import Contract, InvalidContractOptions
from importlinter.domain import fields
from importlinter.domain.imports import Module, DirectImport


class MyContract(Contract):
    string = fields.StringField()
    string_multi = fields.ListField(subfield=fields.StringField())

    module = fields.ModuleField()
    module_multi = fields.ListField(subfield=fields.ModuleField())

    direct_import = fields.DirectImportField()
    direct_import_multi = fields.ListField(subfield=fields.DirectImportField())

    def check(self, *args, **kwargs):
        raise NotImplementedError

    def render_broken_contract(self, *args, **kwargs):
        raise NotImplementedError


def test_valid():
    contract = MyContract(
        name='My contract',
        session_options={},
        contract_options={
            'string': 'Hello',
            'string_multi': ['one', 'two', 'three'],
            'module': 'mypackage.foo',
            'module_multi': ['mypackage.foo', 'mypackage.bar'],
            'direct_import': 'mypackage.foo -> mypackage.bar',
            'direct_import_multi': [
                'mypackage.foo -> mypackage.bar',
                'mypackage.foo -> mypackage.baz',
            ]
        },
    )

    assert contract.string == 'Hello'
    assert contract.string_multi == ['one', 'two', 'three']

    module_foo = Module('mypackage.foo')
    module_bar = Module('mypackage.bar')
    assert contract.module == module_foo
    assert contract.module_multi == [module_foo, module_bar]

    assert contract.direct_import == DirectImport(
        importer=module_foo, imported=module_bar)
    assert contract.direct_import_multi == [
        DirectImport(importer=module_foo, imported=module_bar),
        DirectImport(importer=module_foo, imported=Module('mypackage.baz')),
    ]


# def test_missing():
#     try:
#         MyContract(
#             session_options={},
#             contract_options={
#                 'baz': 'Hello',
#             },
#         )
#     except InvalidContract as e:
#         assert e.errors == {
#             'foo': "This is a required field.",
#             'bar': "This is a required field.",
#         }
#     else:
#         assert False, 'Did not raise InvalidContract.'
#
#
# def test_wrong_type():
#     try:
#         MyContract(
#             session_options={},
#             contract_options={
#                 'foo': ['dfsd'],
#             },
#         )
#     except InvalidContract as e:
#         assert e.errors == {
#             'foo': "This is a required field.",
#             'bar': "This is a required field.",
#         }
#     else:
#         assert False, 'Did not raise InvalidContract.'
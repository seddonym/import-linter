import pytest

from importlinter.domain.contract import (
    Contract, InvalidContractOptions, ContractRegistry, NoSuchContractType,
)
from importlinter.domain import fields


class MyField(fields.Field):
    def parse(self, raw_data):
        if raw_data == 'something invalid':
            raise fields.ValidationError(f'"{raw_data}" is not a valid value.')
        return raw_data


class MyContract(Contract):
    foo = MyField()
    bar = MyField(required=False)

    def check(self, *args, **kwargs):
        raise NotImplementedError

    def render_broken_contract(self, *args, **kwargs):
        raise NotImplementedError


class AnotherContract(Contract):
    def check(self, *args, **kwargs):
        raise NotImplementedError

    def render_broken_contract(self, *args, **kwargs):
        raise NotImplementedError


@pytest.mark.parametrize(
    'contract_options, expected_errors',
    (
        (
            {
                'foo': 'The quick brown fox jumps over the lazy dog.',
                'bar': 'To be, or not to be.'
            },
            None,  # Valid.
        ),
        (
            {},  # No data.
            {
                'foo': "This is a required field.",
            },
        ),
        (
            {
                'foo': 'something invalid',
            },
            {
                'foo': '"something invalid" is not a valid value.',
            },
        ),
    )
)
def test_contract_validation(contract_options, expected_errors):
    contract_kwargs = dict(
        name='My contract',
        session_options={},
        contract_options=contract_options,
    )

    if expected_errors is None:
        contract = MyContract(**contract_kwargs)
        for key, value in contract_options.items():
            assert getattr(contract, key) == value
        return

    try:
        MyContract(**contract_kwargs)
    except InvalidContractOptions as e:
        assert e.errors == expected_errors
    else:
        assert False, 'Did not raise InvalidContractOptions.'  # pragma: nocover


class TestContractRegistry:
    @pytest.mark.parametrize(
        'name, expected_result',
        (
                ('foo', MyContract),
                ('bar', AnotherContract),
                ('baz', NoSuchContractType())
        )
    )
    def test_registry(self, name, expected_result):
        registry = ContractRegistry()

        registry.register(MyContract, name='foo')
        registry.register(AnotherContract, name='bar')

        if isinstance(expected_result, Exception):
            with pytest.raises(NoSuchContractType):
                registry.get_contract_class(name)
        else:
            assert expected_result == registry.get_contract_class(name)

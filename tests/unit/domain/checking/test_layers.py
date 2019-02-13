import pytest

from importlinter.domain.contract import LayerContract
from importlinter.domain.checking import check_contract

from tests.adaptors.graph import FakeGraph


@pytest.mark.parametrize(
    'package_chains, is_valid',
    (
        (
            (
                ('mypackage.high', 'mypackage.medium'),
                ('mypackage.high', 'mypackage.low'),
                ('mypackage.medium', 'mypackage.low'),
            ),
            True,
        ),
        (
            (
                ('mypackage.medium', 'mypackage.high'),
            ),
            False,
        ),
        (
            (
                ('mypackage.low', 'mypackage.high'),
            ),
            False,
        ),
        (
            (
                ('mypackage.low', 'mypackage.medium'),
            ),
            False,
        ),
    )
)
def test_layer_contract_passes(package_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        package_chains=package_chains,
    )

    contract = LayerContract(
        name='Layer contract',
        containers=(
            'mypackage',
        ),
        layers=(
            'high',
            'medium',
            'low',
        ),
    )

    contract_check = check_contract(contract=contract, graph=graph)

    assert contract_check.is_valid == is_valid


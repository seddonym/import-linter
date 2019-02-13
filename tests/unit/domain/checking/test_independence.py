import pytest

from importlinter.domain.contract import IndependenceContract
from importlinter.domain.checking import check_contract

from tests.adaptors.graph import FakeGraph

# TODO finish
@pytest.mark.skip
@pytest.mark.parametrize(
    'package_chains, is_valid',
    (
        (
            (
                ('mypackage.blue', 'medium'),
                ('high', 'low'),
                ('medium', 'low'),
            ),
            True,
        ),
        (
            (
                ('medium', 'high'),
            ),
            False,
        ),
        (
            (
                ('low', 'high'),
            ),
            False,
        ),
        (
            (
                ('low', 'medium'),
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

    contract = IndependenceContract(
        name='Independence contract',
        independent_packages=(
            'mypackage.blue',
            'mypackage.green',
            'mypackage.yellow',
        ),
    )

    contract_check = check_contract(contract=contract, graph=graph)

    assert contract_check.is_valid == is_valid

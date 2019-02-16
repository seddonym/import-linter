import pytest

from importlinter.domain.contract import IndependenceContract
from importlinter.domain.checking import check_contract

from tests.adaptors.graph import FakeGraph


@pytest.mark.parametrize(
    'package_chains, is_valid',
    (
        (
            (
                ('mypackage.blue', 'mypackage.orange'),
                ('mypackage.brown', 'mypackage.blue'),
            ),
            True,
        ),
        (
            (
                ('mypackage.blue', 'mypackage.green'),
            ),
            False,
        ),
        (
            (
                ('mypackage.green', 'mypackage.blue'),
            ),
            False,
        ),
        (
            (
                ('mypackage.blue', 'mypackage.yellow'),
            ),
            False,
        ),
        (
            (
                ('mypackage.yellow', 'mypackage.blue'),
            ),
            False,
        ),
        (
            (
                ('mypackage.green', 'mypackage.yellow'),
            ),
            False,
        ),
        (
            (
                ('mypackage.yellow', 'mypackage.green'),
            ),
            False,
        ),
    )
)
def test_independence_contract(package_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        package_chains=package_chains,
    )

    contract = IndependenceContract(
        name='Independence contract',
        modules=(
            'mypackage.blue',
            'mypackage.green',
            'mypackage.yellow',
        ),
    )

    contract_check = check_contract(contract=contract, graph=graph)

    assert contract_check.is_valid == is_valid

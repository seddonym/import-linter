import pytest

from importlinter.domain.contract import IndependenceContract
from importlinter.domain.checking import check_contract

from tests.adaptors.graph import FakeGraph


@pytest.mark.parametrize(
    'shortest_chains, is_valid',
    (
        (
            {
                ('blue', 'orange'): ('blue', 'orange'),
                ('brown', 'blue'): ('brown', 'blue'),
            },
            True,
        ),
        (
            {
                ('blue', 'green'): ('blue', 'green'),
            },
            False,
        ),
        (
            {
                ('blue.beta.foo', 'green'): ('blue.beta.foo', 'green'),
            },
            False,
        ),
        (
            {
                ('green', 'blue.beta.foo'): ('green', 'blue.beta.foo'),
            },
            False,
        ),
        (
            {
                ('blue', 'yellow'): ('blue', 'yellow'),
            },
            False,
        ),
        (
            {
                ('blue.beta.foo', 'yellow.gamma'): ('blue.beta.foo', 'yellow.gamma'),
            },
            False,
        ),
        (
            {
                ('yellow', 'blue'): ('yellow', 'blue'),
            },
            False,
        ),
        (
            {
                ('green', 'yellow'): ('green', 'yellow'),
            },
            False,
        ),
        (
            {
                ('yellow', 'green'): ('yellow', 'green'),
            },
            False,
        ),
    )
)
def test_independence_contract(shortest_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        descendants={
            'blue': {'alpha', 'beta', 'beta.foo'},
            'yellow': {'gamma', 'delta'},
        },
        shortest_chains=shortest_chains,
    )
    # TODO - test for invalid chains
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

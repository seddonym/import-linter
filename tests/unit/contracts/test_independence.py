import pytest

from importlinter.contracts.independence import IndependenceContract

from tests.adapters.graph import FakeGraph


@pytest.mark.parametrize(
    'shortest_chains, invalid_chains',
    (
        (
            {
                ('blue', 'orange'): ('blue', 'orange'),
                ('brown', 'blue'): ('brown', 'blue'),
            },
            set(),
        ),
        (
            {
                ('blue', 'green'): ('blue', 'green'),
            },
            {
                ('blue', 'green'),
            },
        ),
        (
            {
                ('blue.beta.foo', 'green'): ('blue.beta.foo', 'orange.omega', 'green'),
            },
            {
                ('blue.beta.foo', 'orange.omega', 'green'),
            },
        ),
        (
            {
                ('green', 'blue.beta.foo'): ('green', 'blue.beta.foo'),
            },
            {
                ('green', 'blue.beta.foo'),
            }
        ),
        (
            {
                ('blue', 'yellow'): ('blue', 'yellow'),
            },
            {
                ('blue', 'yellow'),
            },
        ),
        (
            {
                ('blue.beta.foo', 'yellow.gamma'): ('blue.beta.foo', 'yellow.gamma'),
            },
            {
                ('blue.beta.foo', 'yellow.gamma'),
            },
        ),
        (
            {
                ('yellow', 'blue'): ('yellow', 'blue'),
            },
            {
                ('yellow', 'blue'),
            },
        ),
        (
            {
                ('green', 'yellow'): ('green', 'yellow'),
            },
            {
                ('green', 'yellow'),
            },
        ),
        (
            {
                ('yellow', 'green'): ('yellow', 'green'),
            },
            {
                ('yellow', 'green'),
            },
        ),
    )
)
def test_independence_contract(shortest_chains, invalid_chains):
    graph = FakeGraph(
        root_package_name='mypackage',
        descendants={
            'blue': {'alpha', 'beta', 'beta.foo'},
            'yellow': {'gamma', 'delta'},
        },
        shortest_chains=shortest_chains,
    )
    contract = IndependenceContract(
        name='Independence contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'modules': (
                'mypackage.blue',
                'mypackage.green',
                'mypackage.yellow',
            ),
        },
    )

    contract_check = contract.check(graph=graph)

    if invalid_chains:
        assert not contract_check.kept
        absolute_invalid_chains = {
            tuple(
                (f'mypackage.{m}' for m in chain)
            )
            for chain in invalid_chains
        }
        assert absolute_invalid_chains == contract_check.metadata['invalid_chains']
    else:
        assert contract_check.kept

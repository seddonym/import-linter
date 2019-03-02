import pytest

from importlinter.contracts.independence import IndependenceContract
from importlinter.application.app_config import settings
from importlinter.domain.contract import ContractCheck

from tests.adapters.graph import FakeGraph
from tests.adapters.printing import FakePrinter


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


def test_render_broken_contract():
    settings.configure(
        PRINTER=FakePrinter(),
    )
    contract = IndependenceContract(
        name='Independence contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'modules': [
                'mypackage.blue',
                'mypackage.green',
                'mypackage.yellow',
            ],
        },
    )
    check = ContractCheck(
        kept=False,
        metadata={
            'invalid_chains': [
                {
                    'upstream_module': 'mypackage.yellow',
                    'downstream_module': 'mypackage.blue',
                    'chains': [
                        [
                            {
                                'importer': 'mypackage.blue.foo',
                                'imported': 'mypackage.utils.red',
                                'line_numbers': (16, 102),
                            },
                            {
                                'importer': 'mypackage.utils.red',
                                'imported': 'mypackage.utils.brown',
                                'line_numbers': (1,),
                            },
                            {
                                'importer': 'mypackage.utils.brown',
                                'imported': 'mypackage.yellow.bar',
                                'line_numbers': (3,),
                            },
                        ],
                        [
                            {
                                'importer': 'mypackage.blue.bar',
                                'imported': 'mypackage.yellow.baz',
                                'line_numbers': (5,),
                            },
                        ],
                    ],
                },
                {
                    'upstream_module': 'mypackage.green',
                    'downstream_module': 'mypackage.yellow',
                    'chains': [
                        [
                            {
                                'importer': 'mypackage.yellow.foo',
                                'imported': 'mypackage.green.bar',
                                'line_numbers': (15),
                            },
                        ],
                    ],
                },
            ],
        },
    )

    contract.render_broken_contract(check)

    settings.PRINTER.pop_and_assert(
        """
        mypackage.blue is not allowed to import mypackage.yellow:

        -   mypackage.blue.foo -> mypackage.utils.red (l.16, l.102)
            mypackage.utils.red -> mypackage.utils.brown (l.1)
            mypackage.utils.brown -> mypackage.yellow.bar (l.3)

        -   mypackage.blue.bar -> mypackage.yellow.baz (l.5)


        mypackage.green is not allowed to import mypackage.yellow:

        -   mypackage.yellow.foo -> mypackage.green.bar (l.15)


        """
    )
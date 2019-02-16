import pytest

from importlinter.domain.contract import LayerContract
from importlinter.domain.checking import check_contract

from tests.adaptors.graph import FakeGraph


@pytest.mark.parametrize(
    'shortest_chains, is_valid',
    (
        (
            {
                ('high.green', 'medium.orange'): (
                    ('high.green', 'medium.orange'),
                ),
                ('high.green', 'low.white.gamma'): (
                    ('high.green', 'low.white.gamma'),
                ),
                ('medium.orange', 'low.white'): (
                    ('medium.orange', 'low.white'),
                ),
            },
            True,
        ),
        (
            {
                ('medium.orange', 'high.green'): (
                    ('medium.orange', 'high.green'),
                ),
            },
            False,
        ),
        (
            {
                ('low.white.gamma', 'high.yellow.alpha'): (
                    ('low.white.gamma', 'high.yellow.alpha'),
                ),
            },
            False,
        ),
        (
            {
                ('low.white.gamma', 'medium.red'): (
                    ('low.white.gamma', 'medium.red'),
                ),
            },
            False,
        ),
    )
)
def test_layer_contract_single_containers(shortest_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        descendants={
            'high': {
                'green', 'blue', 'yellow', 'yellow.alpha',
            },
            'medium': {
                'orange', 'red', 'orange.beta',
            },
            'low': {
                'black', 'white', 'white.gamma',
            },
        },
        shortest_chains=shortest_chains,
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


@pytest.mark.parametrize(
    'shortest_chains, is_valid',
    (
        (
            {
                ('one.high.green', 'one.medium.orange'): (
                    ('one.high.green', 'one.medium.orange'),
                ),
                ('one.high.green', 'one.low.white.gamma'): (
                    ('one.high.green', 'one.low.white.gamma'),
                ),
                ('one.medium.orange', 'one.low.white'): (
                    ('one.medium.orange', 'one.low.white'),
                ),
                ('two.high.red.alpha', 'two.medium.green.beta'): (
                    'two.high.red.alpha', 'two.medium.green.beta'
                ),
                ('two.high.red.alpha', 'two.low.blue.gamma'): (
                    'two.high.red.alpha', 'two.low.blue.gamma'
                ),
                ('two.medium.green.beta', 'two.low.blue.gamma'): (
                    'two.medium.green.beta', 'two.low.blue.gamma'
                ),
                ('three.high.white', 'three.medium.purple'): (
                    'three.high.white', 'three.medium.purple'
                ),
                ('three.high.white', 'three.low.cyan'): (
                    'three.high.white', 'three.low.cyan'
                ),
                ('three.medium.purple', 'three.low.cyan'): (
                    'three.medium.purple', 'three.low.cyan'
                ),
            },
            True,
        ),
        (
            {
                ('two.medium.green.beta', 'one.high.green'): (
                    'two.medium.green.beta', 'one.high.green',
                ),
            },
            True,
        ),
        (
            {
                    ('three.low.cyan', 'two.high.red.alpha'): (
                    'three.low.cyan', 'two.high.red.alpha'
                ),
            },
            True,
        ),
        (
            {
                ('two.medium.green.beta', 'two.high.red.alpha'): (
                    'two.medium.green.beta', 'two.high.red.alpha'
                ),
            },
            False,
        ),
    )
)
def test_layer_contract_multiple_containers(shortest_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        descendants={
            'one.high': {
                'green', 'blue', 'yellow', 'yellow.alpha',
            },
            'one.medium': {
                'orange', 'red', 'orange.beta',
            },
            'one.low': {
                'black', 'white', 'white.gamma',
            },
            'two.high': {
                'red', 'red.alpha',
            },
            'two.medium': {
                'green', 'green.beta',
            },
            'two.low': {
                'blue', 'blue.gamma',
            },
            'three.high': {
                'white',
            },
            'three.medium': {
                'purple',
            },
            'three.low': {
                'cyan',
            },
        },
        shortest_chains=shortest_chains,
    )

    contract = LayerContract(
        name='Layer contract',
        containers=(
            'mypackage.one',
            'mypackage.two',
            'mypackage.three',
        ),
        layers=(
            'high',
            'medium',
            'low',
        ),
    )

    contract_check = check_contract(contract=contract, graph=graph)

    assert contract_check.is_valid == is_valid


def test_layer_contract_broken_details():
    graph = FakeGraph(
        root_package='mypackage',
        descendants={
            'high': (
                'green', 'blue', 'yellow', 'yellow.alpha',
            ),
            'medium': (
                'orange', 'red', 'orange.beta',
            ),
            'low': (
                'black', 'white', 'white.gamma',
            ),
        },
        shortest_chains={
            ('low.white.gamma', 'high.yellow.alpha'): (
                'low.white.gamma', 'utils.foo', 'utils.bar', 'high.yellow.alpha',
            ),
            ('medium.orange.beta', 'high.blue'): (
                'medium.orange.beta', 'high.blue',
            ),
            ('low.black', 'medium.red'): (
                'low.black', 'utils.baz', 'medium.red',
            ),
        }
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

    assert contract_check.is_valid is False

    assert contract_check.invalid_chains == {
        ('mypackage.low.white.gamma', 'mypackage.utils.foo', 'mypackage.utils.bar', 'mypackage.high.yellow.alpha'),
        ('mypackage.medium.orange.beta', 'mypackage.high.blue'),
        ('mypackage.low.black', 'mypackage.utils.baz', 'mypackage.medium.red'),
    }

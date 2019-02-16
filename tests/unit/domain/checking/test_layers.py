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
def test_layer_contract_single_containers(package_chains, is_valid):
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


@pytest.mark.parametrize(
    'package_chains, is_valid',
    (
        (
            (
                ('mypackage.one.high', 'mypackage.one.medium'),
                ('mypackage.one.high', 'mypackage.one.low'),
                ('mypackage.one.medium', 'mypackage.one.low'),
                ('mypackage.two.high', 'mypackage.two.medium'),
                ('mypackage.two.high', 'mypackage.two.low'),
                ('mypackage.two.medium', 'mypackage.two.low'),
                ('mypackage.three.high', 'mypackage.three.medium'),
                ('mypackage.three.high', 'mypackage.three.low'),
                ('mypackage.three.medium', 'mypackage.three.low'),
            ),
            True,
        ),
        (
            (
                ('mypackage.two.medium', 'mypackage.one.high'),
            ),
            True,
        ),
        (
            (
                ('mypackage.three.low', 'mypackage.two.high'),
            ),
            True,
        ),
        (
            (
                ('mypackage.two.medium', 'mypackage.two.high'),
            ),
            False,
        ),
    )
)
def test_layer_contract_multiple_containers(package_chains, is_valid):
    graph = FakeGraph(
        root_package='mypackage',
        package_chains=package_chains,
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
                ('low.white.gamma', 'utils.foo', 'utils.bar', 'high.yellow.alpha'),
            ),
            ('medium.orange.beta', 'high.blue'): (
                ('medium.orange.beta', 'high.blue'),
            ),
            ('low.black', 'medium.red'): (
                ('low.black', 'utils.baz', 'medium.red'),
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

    assert contract_check.invalid_chains == (
        'mypackage.low.white.gamma', 'mypackage.utils.foo', 'mypackage.utils.bar',
        'mypackage.high.yellow.alpha',
    )

import pytest

from importlinter.contracts.layers import LayersContract
from importlinter.domain.helpers import MissingImport

from tests.adapters.graph import FakeGraph


@pytest.mark.parametrize(
    'shortest_chains, is_kept',
    (
        (
            {
                ('high.green', 'medium.orange'): (
                    'high.green', 'medium.orange',
                ),
                ('high.green', 'low.white.gamma'): (
                    'high.green', 'low.white.gamma',
                ),
                ('medium.orange', 'low.white'): (
                    'medium.orange', 'low.white',
                ),
            },
            True,
        ),
        (
            {
                ('medium.orange', 'high.green'): (
                    'medium.orange', 'high.green',
                ),
            },
            False,
        ),
        (
            {
                ('low.white.gamma', 'high.yellow.alpha'): (
                    'low.white.gamma', 'high.yellow.alpha',
                ),
            },
            False,
        ),
        (
            {
                ('low.white.gamma', 'medium.red'): (
                    'low.white.gamma', 'medium.red',
                ),
            },
            False,
        ),
    )
)
def test_layer_contract_single_containers(shortest_chains, is_kept):
    graph = FakeGraph(
        root_package_name='mypackage',
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

    contract = LayersContract(
        name='Layer contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'containers': [
                'mypackage',
            ],
            'layers': [
                'high',
                'medium',
                'low',
            ],
        },
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept == is_kept


@pytest.mark.parametrize(
    'shortest_chains, is_kept',
    (
        (
            {
                ('one.high.green', 'one.medium.orange'): (
                    'one.high.green', 'one.medium.orange',
                ),
                ('one.high.green', 'one.low.white.gamma'): (
                    'one.high.green', 'one.low.white.gamma',
                ),
                ('one.medium.orange', 'one.low.white'): (
                    'one.medium.orange', 'one.low.white',
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
def test_layer_contract_multiple_containers(shortest_chains, is_kept):
    graph = FakeGraph(
        root_package_name='mypackage',
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

    contract = LayersContract(
        name='Layer contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'containers': [
                'mypackage.one',
                'mypackage.two',
                'mypackage.three',
            ],
            'layers': [
                'high',
                'medium',
                'low',
            ],
        },
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept == is_kept


def test_layer_contract_broken_details():
    graph = FakeGraph(
        root_package_name='mypackage',
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

    contract = LayersContract(
        name='Layer contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'containers': [
                'mypackage',
            ],
            'layers': [
                'high',
                'medium',
                'low',
            ],
        },
    )

    contract_check = contract.check(graph=graph)

    assert contract_check.kept is False

    assert contract_check.metadata['invalid_chains'] == {
        ('mypackage.low.white.gamma', 'mypackage.utils.foo', 'mypackage.utils.bar',
         'mypackage.high.yellow.alpha'),
        ('mypackage.medium.orange.beta', 'mypackage.high.blue'),
        ('mypackage.low.black', 'mypackage.utils.baz', 'mypackage.medium.red'),
    }


@pytest.mark.parametrize(
    'ignore_imports, invalid_chains',
    (
        (
            # Ignore from each chain - should be valid.
            (
                ('utils.baz', 'medium.orange'),
                ('low.white.gamma', 'utils.foo'),
            ),
            set(),
        ),
        (
            # Ignore only one chain - should return the other.
            (
                ('low.white.gamma', 'utils.foo'),
            ),
            {
                ('low.black', 'utils.baz', 'medium.orange'),
            }
        ),
        (
            # Multiple ignore from same path - should allow it.
            (
                ('low.white.gamma', 'utils.foo'),
                ('utils.bar', 'high.yellow.alpha'),
            ),
            {
                ('low.black', 'utils.baz', 'medium.orange'),
            }
        ),
        (
            # Ignore from nonexistent module - should error.
            (
                ('nonexistent.foo', 'utils.foo'),
            ),
            MissingImport(),
        ),
        (
            # Ignore from nonexistent module - should error.
            (
                ('utils.foo', 'nonexistent.foo'),
            ),
            MissingImport(),
        ),
    ),
)
def test_ignore_imports(ignore_imports, invalid_chains):
    graph = FakeGraph(
        root_package_name='mypackage',
        descendants={
            'high': {
                'green', 'blue', 'yellow', 'yellow.alpha',
            },
            'medium': {
                'orange',
            },
            'low': {
                'black', 'white', 'white.gamma',
            },
        },
        shortest_chains={
            ('low.white.gamma', 'high.yellow.alpha'): (
                'low.white.gamma', 'utils.foo', 'utils.bar', 'high.yellow.alpha',
            ),
            ('low.black', 'medium.orange'): (
                'low.black', 'utils.baz', 'medium.orange',
            ),
        },
        import_details=[
            {
                'importer': 'utils.baz',
                'imported': 'medium.orange',
                'line_number': 1,
                'line_contents': 'TODO',
            },
            {
                'importer': 'low.white.gamma',
                'imported': 'utils.foo',
                'line_number': 1,
                'line_contents': 'TODO',
            },
            {
                'importer': 'utils.bar',
                'imported': 'high.yellow.alpha',
                'line_number': 1,
                'line_contents': 'TODO',
            },
        ],
    )

    contract = LayersContract(
        name='Layer contract',
        session_options={
            'root_package_name': 'mypackage',
        },
        contract_options={
            'containers': [
                'mypackage',
            ],
            'layers': [
                'high',
                'medium',
                'low',
            ],
            'ignore_imports': ignore_imports,
        },
    )

    if isinstance(invalid_chains, Exception):
        with pytest.raises(invalid_chains.__class__):
            contract.check(graph=graph)
        return
    else:
        contract_check = contract.check(graph=graph)

    if invalid_chains:
        assert False is contract_check.kept
        absolute_invalid_chains = {
            tuple(
                (f'mypackage.{m}' for m in chain)
            )
            for chain in invalid_chains
        }
        assert absolute_invalid_chains == contract_check.metadata['invalid_chains']
    else:
        assert True is contract_check.kept

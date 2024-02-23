from __future__ import annotations

import pytest
from grimp.adaptors.graph import ImportGraph

from importlinter.application.app_config import settings
from importlinter.contracts.modular import ModularContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.printing import FakePrinter
from tests.adapters.timing import FakeTimer


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=FakeTimer())


class TestModularContract:
    def _build_default_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.blue",
            "mypackage.blue.alpha",
            "mypackage.blue.beta",
            "mypackage.blue.beta.foo",
            "mypackage.blue.foo",
            "mypackage.blue.hello",
            "mypackage.blue.world",
            "mypackage.green",
            "mypackage.green.bar",
            "mypackage.yellow",
            "mypackage.yellow.gamma",
            "mypackage.yellow.delta",
            "mypackage.other",
            "mypackage.other.sub",
            "mypackage.other.sub2",
        ):
            graph.add_module(module)
        return graph

    def _check_default_contract(self, graph):
        contract = ModularContract(
            name="Modular contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={"modules": ("mypackage",)},
        )
        return contract.check(graph=graph, verbose=False)

    def test_when_modules_are_modular(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.green",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert contract_check.kept, contract_check.metadata

    def test_non_modular_bidirectional(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.green",
            line_number=11,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.blue",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {
                "mypackage": [
                    "mypackage.blue <- mypackage.other",
                    "mypackage.other <- mypackage.blue",
                ]
            }
        }

        assert expected_metadata == contract_check.metadata

    def test_non_modular_circular(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.green",
            line_number=11,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.green",
            imported="mypackage.blue",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {
                "mypackage": [
                    "mypackage.blue <- mypackage.green",
                    "mypackage.green <- mypackage.other",
                    "mypackage.other <- mypackage.blue",
                ]
            }
        }
        assert expected_metadata == contract_check.metadata

    def test_non_modular_children_bidirectional(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue.foo",
            imported="mypackage.other.sub",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other.sub2",
            imported="mypackage.blue.world",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {
                "mypackage": [
                    "mypackage.blue <- mypackage.other",
                    "mypackage.other <- mypackage.blue",
                ]
            }
        }
        assert expected_metadata == contract_check.metadata

    def test_non_modular_circular_children(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue.foo",
            imported="mypackage.other.sub",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other.sub2",
            imported="mypackage.green.world",
            line_number=11,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.green.bar",
            imported="mypackage.blue.hello",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {
                "mypackage": [
                    "mypackage.blue <- mypackage.green",
                    "mypackage.green <- mypackage.other",
                    "mypackage.other <- mypackage.blue",
                ]
            }
        }
        assert expected_metadata == contract_check.metadata

    def test_non_modular_circular_children_of_children_of_children(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue.foo.bar.buzz",
            imported="mypackage.other.sub.hello.world",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other.sub2.foo.bar",
            imported="mypackage.green.world.fizz.buzz",
            line_number=11,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.green.bar.hello.goodbye",
            imported="mypackage.blue.hello.world.world",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {
                "mypackage": [
                    "mypackage.blue <- mypackage.green",
                    "mypackage.green <- mypackage.other",
                    "mypackage.other <- mypackage.blue",
                ]
            }
        }
        assert expected_metadata == contract_check.metadata


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = ModularContract(
        name="Modular contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={"modules": ["mypackage", "mypackage.green"]},
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "violations": {
                "mypackage": [
                    "mypackage.blue.foo <- mypackage.utils.red",
                    "mypackage.blue.red <- mypackage.utils.yellow",
                ],
                "mypackage.green": [
                    "mypackage.green.a.b <- mypackage.green.b.a",
                ],
            }
        },
    )

    contract.render_broken_contract(check)

    settings.PRINTER.pop_and_assert(
        """
        child modules of mypackage must be modular and thus circular dependencies are not allowed:

        - mypackage.blue.foo <- mypackage.utils.red
        - mypackage.blue.red <- mypackage.utils.yellow

        child modules of mypackage.green must be modular and thus circular dependencies are not allowed:

        - mypackage.green.a.b <- mypackage.green.b.a

        """  # noqa
    )

from __future__ import annotations

import pytest
from grimp.adaptors.graph import ImportGraph

from importlinter.application.app_config import settings
from importlinter.contracts.standalone import StandaloneContract
from importlinter.domain.contract import ContractCheck
from tests.adapters.printing import FakePrinter
from tests.adapters.timing import FakeTimer


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=FakeTimer())


class TestStandaloneContract:
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
        contract = StandaloneContract(
            name="Standalone contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={"modules": ("mypackage.green", "mypackage.yellow")},
        )
        return contract.check(graph=graph, verbose=False)

    def test_when_modules_are_standalone(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.blue.world",
            line_number=11,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert contract_check.kept, contract_check.metadata

    def test_non_standalone_imported(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.blue",
            imported="mypackage.green",
            line_number=10,
            line_contents="-",
        )
        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {"mypackage.green": [("mypackage.green", "mypackage.blue")]}
        }
        assert expected_metadata == contract_check.metadata

    def test_non_standalone_imports(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.yellow",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )

        contract_check = self._check_default_contract(graph)

        assert not contract_check.kept

        expected_metadata = {
            "violations": {"mypackage.yellow": [("mypackage.other", "mypackage.yellow")]}
        }
        assert expected_metadata == contract_check.metadata

    def test_standalone_ignore(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.yellow",
            imported="mypackage.other",
            line_number=10,
            line_contents="-",
        )

        contract = StandaloneContract(
            name="Standalone contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={
                "modules": ("mypackage.green", "mypackage.yellow"),
                "ignore_imports": ["mypackage.yellow -> mypackage.other"],
            },
        )
        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept


def test_render_broken_contract():
    settings.configure(PRINTER=FakePrinter())
    contract = StandaloneContract(
        name="Standalone contract",
        session_options={"root_packages": ["mypackage"]},
        contract_options={"modules": ["mypackage.green"]},
    )
    check = ContractCheck(
        kept=False,
        metadata={
            "violations": {
                "mypackage": [
                    ("mypackage.blue.foo", "mypackage.utils.red"),
                    ("mypackage.blue.red", "mypackage.utils.yellow"),
                ],
                "mypackage.green": [
                    ("mypackage.green.a.b", "mypackage.green.b.a"),
                ],
            }
        },
    )

    contract.render_broken_contract(check)

    settings.PRINTER.pop_and_assert(
        """
        mypackage must be standalone:

        - mypackage.utils.red is not allowed to import mypackage.blue.foo
        - mypackage.utils.yellow is not allowed to import mypackage.blue.red

        mypackage.green must be standalone:

        - mypackage.green.b.a is not allowed to import mypackage.green.a.b

        """  # noqa
    )

"""
Benchmarks of contracts, using a fake graph.

When the tests are run normally (`--benchmark-disable`), each benchmark is run once and not timed,
so it is checked like any other test. To time them, use `just benchmark-local`.
"""

from __future__ import annotations

from copy import deepcopy

import pytest
from grimp import ImportGraph

from importlinter.adapters.timing import SystemClockTimer
from importlinter.application.app_config import settings
from importlinter.contracts.acyclic_siblings import AcyclicSiblingsContract
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.contracts.independence import IndependenceContract
from importlinter.contracts.layers import LayersContract
from importlinter.contracts.protected import ProtectedContract

from . import graph as fake_graph


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=SystemClockTimer())


@pytest.fixture(scope="module")
def _kept_graph() -> ImportGraph:
    return fake_graph.build_graph()


@pytest.fixture
def graph(_kept_graph) -> ImportGraph:
    # Copy because checking a contract may mutate the graph.
    # e.g. removing imports from ignore_imports.
    return deepcopy(_kept_graph)


class TestForbidden:
    @staticmethod
    def _build_contract() -> ForbiddenContract:
        return ForbiddenContract(
            name="Data must not import anything else",
            session_options={"root_packages": [fake_graph._ROOT_PACKAGE]},
            contract_options={
                "source_modules": ["mypkg.data"],
                "forbidden_modules": ["mypkg.**"],
            },
        )

    def test_kept(self, graph, benchmark):
        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert contract_check.kept

    def test_broken(self, graph, benchmark):
        # Add violations
        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=100)

        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert not contract_check.kept


class TestProtected:
    @staticmethod
    def _build_contract() -> ProtectedContract:
        return ProtectedContract(
            name="Application must only be imported by the plugins",
            session_options={"root_packages": [fake_graph._ROOT_PACKAGE]},
            contract_options={
                "protected_modules": ["mypkg.application"],
                "allowed_importers": ["mypkg.plugins"],
            },
        )

    def test_kept(self, graph, benchmark):
        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert contract_check.kept

    def test_broken(self, graph, benchmark):
        # Add violations
        fake_graph.add_imports(
            graph, importer_layer="domain", imported_layer="application", count=100
        )

        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert not contract_check.kept


class TestLayers:
    @staticmethod
    def _build_contract() -> LayersContract:
        return LayersContract(
            name="Application, domain and data are layered",
            session_options={"root_packages": [fake_graph._ROOT_PACKAGE]},
            contract_options={
                "layers": [
                    "mypkg.plugins",
                    "mypkg.application",
                    "mypkg.domain",
                    "mypkg.data",
                ],
            },
        )

    def test_kept(self, graph, benchmark):
        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert contract_check.kept

    def test_broken(self, graph, benchmark):
        # Add violations
        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=100)

        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert not contract_check.kept


class TestIndependence:
    @staticmethod
    def _build_contract() -> IndependenceContract:
        return IndependenceContract(
            name="Plugins are independent",
            session_options={"root_packages": [fake_graph._ROOT_PACKAGE]},
            contract_options={
                "modules": ["mypkg.plugins.red", "mypkg.plugins.green", "mypkg.plugins.blue"],
            },
        )

    def test_kept(self, graph, benchmark):
        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert contract_check.kept

    def test_broken(self, graph, benchmark):
        # Add violations
        fake_graph.add_imports(
            graph, importer_layer="plugins.red", imported_layer="plugins.green", count=100
        )

        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert not contract_check.kept


class TestAcyclicSiblings:
    @staticmethod
    def _build_contract() -> AcyclicSiblingsContract:
        return AcyclicSiblingsContract(
            name="There are no cycles between siblings",
            session_options={"root_packages": [fake_graph._ROOT_PACKAGE]},
            contract_options={"ancestors": ["mypkg"]},
        )

    def test_kept(self, graph, benchmark):
        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert contract_check.kept

    def test_broken(self, graph, benchmark):
        # Add violations. The domain already imports the data layer, so this makes a cycle.
        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=100)

        contract = self._build_contract()
        contract_check = benchmark(contract.check, graph, verbose=False)
        assert not contract_check.kept

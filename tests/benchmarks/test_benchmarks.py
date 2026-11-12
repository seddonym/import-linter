"""
Performance benchmarks, run with pytest-codspeed.

Run locally with:

    uv run pytest tests/benchmarks --codspeed
"""

from __future__ import annotations

import os
from copy import deepcopy
import random
from pathlib import Path

import grimp
import pytest

from importlinter.application import use_cases
from importlinter.application.app_config import settings
from importlinter.configuration import configure
from importlinter.contracts.acyclic_siblings import AcyclicSiblingsContract
from importlinter.contracts.forbidden import ForbiddenContract
from importlinter.contracts.independence import IndependenceContract
from importlinter.contracts.layers import LayersContract
from importlinter.contracts.protected import ProtectedContract
from importlinter.domain.contract import Contract

from tests.adapters.timing import FakeTimer

REPO_ROOT = Path(__file__).parent.parent.parent

ROOT = "bench"
# Ordered from highest to lowest.
LAYERS = [f"layer{i}" for i in range(8)]
CHILDREN_PER_LAYER = 6
GRANDCHILDREN_PER_CHILD = 6
IMPORTS_PER_MODULE = 4


@pytest.fixture(scope="module", autouse=True)
def configure_settings():
    settings.configure(TIMER=FakeTimer())


def _build_synthetic_graph(illegal_import_count: int) -> grimp.ImportGraph:
    """
    Build a deterministic synthetic import graph of roughly 350 modules.

    Most imports go downward through the layers (i.e. they are legal for a layers contract
    where layer0 is the highest), with a configurable number of upward imports added.
    """
    rng = random.Random(1234)
    graph = grimp.ImportGraph()
    graph.add_module(ROOT)

    modules_by_layer: dict[int, list[str]] = {}
    for layer_index, layer in enumerate(LAYERS):
        layer_module = f"{ROOT}.{layer}"
        modules = [layer_module]
        for child_index in range(CHILDREN_PER_LAYER):
            child = f"{layer_module}.child{child_index}"
            modules.append(child)
            for grandchild_index in range(GRANDCHILDREN_PER_CHILD):
                modules.append(f"{child}.mod{grandchild_index}")
        for module in modules:
            graph.add_module(module)
        modules_by_layer[layer_index] = modules

    line_number = 1
    for layer_index, modules in modules_by_layer.items():
        for importer in modules:
            for _ in range(IMPORTS_PER_MODULE):
                # Import from the same layer or any lower layer.
                imported_layer = rng.randint(layer_index, len(LAYERS) - 1)
                imported = rng.choice(modules_by_layer[imported_layer])
                if imported == importer:
                    continue
                graph.add_import(
                    importer=importer,
                    imported=imported,
                    line_number=line_number,
                    line_contents=f"import {imported}",
                )
                line_number += 1

    for _ in range(illegal_import_count):
        importer_layer = rng.randint(1, len(LAYERS) - 1)
        imported_layer = rng.randint(0, importer_layer - 1)
        importer = rng.choice(modules_by_layer[importer_layer])
        imported = rng.choice(modules_by_layer[imported_layer])
        graph.add_import(
            importer=importer,
            imported=imported,
            line_number=line_number,
            line_contents=f"import {imported}",
        )
        line_number += 1

    return graph


@pytest.fixture(scope="module")
def clean_graph() -> grimp.ImportGraph:
    return _build_synthetic_graph(illegal_import_count=0)


@pytest.fixture(scope="module")
def broken_graph() -> grimp.ImportGraph:
    return _build_synthetic_graph(illegal_import_count=20)


def _check_contract(benchmark, contract: Contract, graph: grimp.ImportGraph):
    # Some contracts mutate the graph while checking, so give each round a fresh copy.
    def setup():
        return (deepcopy(graph),), {}

    def run(graph_copy):
        return contract.check(graph=graph_copy, verbose=False)

    return benchmark.pedantic(run, setup=setup, rounds=1, iterations=1)


SESSION_OPTIONS = {"root_packages": [ROOT]}


@pytest.mark.parametrize("graph_name", ["clean_graph", "broken_graph"])
def test_layers_contract(benchmark, request, graph_name):
    graph = request.getfixturevalue(graph_name)
    contract = LayersContract(
        name="Layers",
        session_options=SESSION_OPTIONS,
        contract_options={"layers": [f"{ROOT}.{layer}" for layer in LAYERS]},
    )

    check = _check_contract(benchmark, contract, graph)

    assert check.kept is (graph_name == "clean_graph")


def test_layers_contract_with_containers(benchmark, broken_graph):
    contract = LayersContract(
        name="Layers with containers",
        session_options=SESSION_OPTIONS,
        contract_options={
            "containers": [f"{ROOT}.{layer}" for layer in LAYERS],
            "layers": [
                "child0",
                "child1 | child2",
                "child3 : child4",
                "child5",
            ],
        },
    )

    _check_contract(benchmark, contract, broken_graph)


def test_independence_contract(benchmark, broken_graph):
    contract = IndependenceContract(
        name="Independence",
        session_options=SESSION_OPTIONS,
        contract_options={"modules": [f"{ROOT}.{layer}.child0" for layer in LAYERS[:4]]},
    )

    _check_contract(benchmark, contract, broken_graph)


def test_independence_contract_with_wildcard(benchmark, broken_graph):
    contract = IndependenceContract(
        name="Independence with wildcard",
        session_options=SESSION_OPTIONS,
        contract_options={"modules": [f"{ROOT}.{LAYERS[-1]}.*"]},
    )

    _check_contract(benchmark, contract, broken_graph)


def test_forbidden_contract(benchmark, broken_graph):
    contract = ForbiddenContract(
        name="Forbidden",
        session_options=SESSION_OPTIONS,
        contract_options={
            "source_modules": [f"{ROOT}.{layer}" for layer in LAYERS[4:]],
            "forbidden_modules": [f"{ROOT}.{layer}" for layer in LAYERS[:2]],
        },
    )

    check = _check_contract(benchmark, contract, broken_graph)

    assert check.kept is False


def test_protected_contract(benchmark, broken_graph):
    contract = ProtectedContract(
        name="Protected",
        session_options=SESSION_OPTIONS,
        contract_options={
            "protected_modules": [f"{ROOT}.{LAYERS[-1]}.child0"],
            "allowed_importers": [f"{ROOT}.{LAYERS[-1]}"],
        },
    )

    _check_contract(benchmark, contract, broken_graph)


def test_acyclic_siblings_contract(benchmark, broken_graph):
    contract = AcyclicSiblingsContract(
        name="Acyclic siblings",
        session_options=SESSION_OPTIONS,
        contract_options={"ancestors": [ROOT]},
    )

    _check_contract(benchmark, contract, broken_graph)


@pytest.fixture
def real_settings():
    """
    Use the real adapters (filesystem, graph builder) for end-to-end benchmarks.
    """
    original_cwd = os.getcwd()
    os.chdir(REPO_ROOT)
    configure()
    yield
    os.chdir(original_cwd)
    settings.configure(TIMER=FakeTimer())


def test_build_graph_of_importlinter(benchmark, real_settings):
    graph = benchmark(grimp.build_graph, "importlinter", cache_dir=None)

    assert "importlinter.application.use_cases" in graph.modules


def test_lint_imports_end_to_end(benchmark, real_settings):
    """
    Lint import-linter's own architecture using its .importlinter config, without caching.
    """
    result = benchmark(
        use_cases.lint_imports,
        config_filename=str(REPO_ROOT / ".importlinter"),
        cache_dir=None,
        no_logo=True,
    )

    assert result == use_cases.SUCCESS

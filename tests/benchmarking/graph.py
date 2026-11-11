"""
A fake graph for benchmarking.

The graph has the shape of a layered application, with plugins:

    mypkg
        data
        domain
        application
        plugins
            red
            green
            blue

Each layer has 1000 modules, e.g. mypkg.data.000 to mypkg.data.999.

The layers import each other like so (the numbers are the number of imports):

    application --10000--> domain --10000--> data
    plugins.red, plugins.green, plugins.blue --5000--> domain
    plugins.red, plugins.green, plugins.blue --5000--> application

The graph is built so that it satisfies contracts that say that the lower layers must not import
the higher ones. To benchmark a contract that is broken, use add_imports to add imports that break
the contract.
"""

from __future__ import annotations

import random

from grimp import ImportGraph

_ROOT_PACKAGE = "mypkg"

_LAYERS = ("data", "domain", "application", "plugins.red", "plugins.green", "plugins.blue")

_MODULES_PER_LAYER = 1000

# The number of imports between the layers: (importer, imported): number of imports.
_IMPORT_COUNTS: dict[tuple[str, str], int] = {
    ("domain", "data"): 10000,
    ("application", "domain"): 10000,
    ("plugins.red", "domain"): 5000,
    ("plugins.green", "domain"): 5000,
    ("plugins.blue", "domain"): 5000,
    ("plugins.red", "application"): 5000,
    ("plugins.green", "application"): 5000,
    ("plugins.blue", "application"): 5000,
}

# Every pair of module numbers, e.g. (0, 0), (0, 1), ..., (999, 999), in a random order. The order is
# the same every time. Importing the first N pairs gives N imports, in a random-looking pattern.
_IMPORT_ORDER: list[tuple[int, int]] = [
    (importer, imported)
    for importer in range(_MODULES_PER_LAYER)
    for imported in range(_MODULES_PER_LAYER)
]
# Seed shuffle for deterministic results.
random.Random(0).shuffle(_IMPORT_ORDER)


def build_graph() -> ImportGraph:
    """
    Build a graph in which the lower layers don't import the higher layers.
    """
    graph = ImportGraph()

    for layer in _LAYERS:
        for number in range(_MODULES_PER_LAYER):
            _add_module(graph, _module_name(layer, number))

    for (importer_layer, imported_layer), count in _IMPORT_COUNTS.items():
        add_imports(graph, importer_layer, imported_layer, count)

    return graph


def add_imports(graph: ImportGraph, importer_layer: str, imported_layer: str, count: int) -> None:
    """
    Add imports of modules in the imported layer by modules in the importer layer to the graph.

    This adds `count` imports that weren't in the graph already, so calling it again adds more. The
    modules are chosen by going through _IMPORT_ORDER and skipping the imports that are already in
    the graph, so the results are deterministic.
    """
    added_count = 0
    for importer_number, imported_number in _IMPORT_ORDER:
        if added_count == count:
            break
        importer = _module_name(importer_layer, importer_number)
        imported = _module_name(imported_layer, imported_number)
        if graph.direct_import_exists(importer=importer, imported=imported):
            continue
        graph.add_import(
            importer=importer,
            imported=imported,
            line_number=1,
            line_contents=f"import {imported}",
        )
        added_count += 1

    if added_count < count:
        raise ValueError(
            f"Cannot add {count} imports of {imported_layer} by {importer_layer}: "
            f"only {added_count} are possible."
        )


def _add_module(graph: ImportGraph, module: str) -> None:
    """
    Add the module and all of its ancestors to the graph.
    """
    parts = module.split(".")
    for depth in range(1, len(parts) + 1):
        graph.add_module(".".join(parts[:depth]))


def _module_name(layer: str, number: int) -> str:
    """
    Return the name of the module with the number in the layer, e.g. mypkg.plugins.red.007.
    """
    return f"{_ROOT_PACKAGE}.{layer}.{number:03d}"

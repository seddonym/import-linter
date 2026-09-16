from __future__ import annotations

import logging
from dataclasses import dataclass

import grimp
from collections.abc import Set

from importlinter.application.use_cases import build_dot_graph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModuleDot:
    """Dot graph of the module, together with some metadata needed for rendering."""

    dot_string: str
    module: str
    # Any children that are packages, and therefore can be drilled down into.
    child_packages: Set[str]


def _get_grimp_graph(
    cache: dict[tuple[str, ...], grimp.ImportGraph], root_packages: list[str]
) -> grimp.ImportGraph:
    # A single graph is built containing all the root packages, so that dependencies between
    # them are captured.
    key = tuple(root_packages)
    if key not in cache:
        joined = ", ".join(f"'{package}'" for package in root_packages)
        logger.info(f"Building grimp graph for {joined}...")
        cache[key] = grimp.build_graph(*root_packages)
        logger.info(f"Grimp graph for {joined} built.")
    return cache[key]


def generate_dot(
    cache: dict[tuple[str, ...], grimp.ImportGraph],
    module: str,
    show_import_totals: bool,
    show_module_counts: bool,
    show_lazy_imports: bool,
    show_cycle_breakers: bool,
    root_packages: list[str],
) -> ModuleDot:
    logger.info(f"Building graph for module '{module}'...")
    grimp_graph = _get_grimp_graph(cache, root_packages)

    if module:
        dot_graph = build_dot_graph(
            grimp_graph,
            module,
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
        )
        child_packages = _get_child_packages(grimp_graph, module)
    else:
        # Top-level overview of all the root packages together.
        dot_graph = build_dot_graph(
            grimp_graph,
            module,
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
            modules=root_packages,
        )
        child_packages = {
            "." + package.split(".")[-1]
            for package in root_packages
            if grimp_graph.find_children(package)
        }

    dot_string = dot_graph.render()

    logger.info(f"Graph for '{module}' built ({len(child_packages)} packages).")
    return ModuleDot(dot_string=dot_string, module=module, child_packages=child_packages)


def _get_child_packages(grimp_graph: grimp.ImportGraph, module: str) -> set[str]:
    children = grimp_graph.find_children(module)
    child_packages = set()
    for child in children:
        grandchildren = grimp_graph.find_children(child)
        if grandchildren:
            relative_name = "." + child.split(".")[-1]
            child_packages.add(relative_name)
    return child_packages

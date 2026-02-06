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
    cache: dict[str, grimp.ImportGraph], top_level_package: str
) -> grimp.ImportGraph:
    if top_level_package not in cache:
        logger.info(f"Building grimp graph for '{top_level_package}'...")
        cache[top_level_package] = grimp.build_graph(top_level_package)
        logger.info(f"Grimp graph for '{top_level_package}' built.")
    return cache[top_level_package]


def generate_dot(
    cache: dict[str, grimp.ImportGraph],
    module: str,
    show_import_totals: bool,
    show_cycle_breakers: bool,
) -> ModuleDot:
    logger.info(f"Building graph for module '{module}'...")
    top_level_package = module.split(".")[0]
    grimp_graph = _get_grimp_graph(cache, top_level_package)

    dot_graph = build_dot_graph(grimp_graph, module, show_import_totals, show_cycle_breakers)
    dot_string = dot_graph.render()

    child_packages = _get_child_packages(grimp_graph, module)

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

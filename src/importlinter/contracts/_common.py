"""
Helper functions used by more than one contract type.

Code in here should not be relied upon as a public API; if you're
relying on it for a custom contract type, be aware things may change
without warning.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

import grimp
from typing_extensions import TypedDict

from importlinter.application import output


class Link(TypedDict):
    importer: str
    imported: str
    # If the graph has been built manually, we may not know the line number.
    line_numbers: tuple[int | None, ...]


Chain = list[Link]


class DetailedChain(TypedDict):
    chain: Chain
    extra_firsts: list[Link]
    extra_lasts: list[Link]


class ModulePairChains(TypedDict):
    """
    The chains found between a single pair of modules.
    """

    upstream_module: str
    downstream_module: str
    chains: list[DetailedChain]


def render_chain_data(chain_data: DetailedChain) -> None:
    main_chain = chain_data["chain"]
    _render_direct_import(main_chain[0], extra_firsts=chain_data["extra_firsts"], first_line=True)

    for direct_import in main_chain[1:-1]:
        _render_direct_import(direct_import)

    if len(main_chain) > 1:
        _render_direct_import(main_chain[-1], extra_lasts=chain_data["extra_lasts"])


def format_line_numbers(line_numbers: Sequence[int | None]) -> str:
    """
    Return a human-readable string of the supplied line numbers.

    Unknown line numbers should be provided as a None value in the sequence. E.g.
    (None,) will be returned as "l.?".
    """
    return ", ".join(
        "l.?" if line_number is None else f"l.{line_number}" for line_number in line_numbers
    )


def _render_direct_import(
    direct_import,
    first_line: bool = False,
    extra_firsts: list | None = None,
    extra_lasts: list | None = None,
) -> None:
    import_strings = []
    if extra_firsts:
        for position, source in enumerate([direct_import] + extra_firsts[:-1]):
            prefix = "& " if position > 0 else ""
            importer = source["importer"]
            line_numbers = format_line_numbers(source["line_numbers"])
            import_strings.append(f"{prefix}{importer} ({line_numbers})")
        importer, imported = extra_firsts[-1]["importer"], extra_firsts[-1]["imported"]
        line_numbers = format_line_numbers(extra_firsts[-1]["line_numbers"])
        import_strings.append(f"& {importer} -> {imported} ({line_numbers})")
    else:
        importer, imported = direct_import["importer"], direct_import["imported"]
        line_numbers = format_line_numbers(direct_import["line_numbers"])
        import_strings.append(f"{importer} -> {imported} ({line_numbers})")

    if extra_lasts:
        indent_string = (len(direct_import["importer"]) + 4) * " "
        for destination in extra_lasts:
            imported = destination["imported"]
            line_numbers = format_line_numbers(destination["line_numbers"])
            import_strings.append(f"{indent_string}& {imported} ({line_numbers})")

    for position, import_string in enumerate(import_strings):
        if first_line and position == 0:
            output.print_error(f"- {import_string}", bold=False)
        else:
            output.print_error(f"  {import_string}", bold=False)


def build_detailed_chain_from_route(route: grimp.Route, graph: grimp.ImportGraph) -> DetailedChain:
    ordered_heads = sorted(route.heads)
    extra_firsts: list[Link] = [
        {
            "importer": head,
            "imported": route.middle[0],
            "line_numbers": get_line_numbers(importer=head, imported=route.middle[0], graph=graph),
        }
        for head in ordered_heads[1:]
    ]
    ordered_tails = sorted(route.tails)
    extra_lasts: list[Link] = [
        {
            "imported": tail,
            "importer": route.middle[-1],
            "line_numbers": get_line_numbers(
                imported=tail, importer=route.middle[-1], graph=graph
            ),
        }
        for tail in ordered_tails[1:]
    ]
    chain_as_strings = [ordered_heads[0], *route.middle, ordered_tails[0]]
    return {
        "chain": build_chain_from_module_names(chain_as_strings, graph),
        "extra_firsts": extra_firsts,
        "extra_lasts": extra_lasts,
    }


def build_chain_from_module_names(module_names: Sequence[str], graph: grimp.ImportGraph) -> Chain:
    """
    Return the links between each consecutive pair of the supplied module names.
    """
    return [
        {
            "importer": importer,
            "imported": imported,
            "line_numbers": get_line_numbers(importer=importer, imported=imported, graph=graph),
        }
        for importer, imported in itertools.pairwise(module_names)
    ]


def build_detailed_chain_from_module_names(
    module_names: Sequence[str], graph: grimp.ImportGraph
) -> DetailedChain:
    """
    Return a detailed chain for a chain that was found on its own.

    Chains found individually have no shared heads or tails to collapse, so the extras are
    always empty; the shape matches the chains built from routes so that both render identically.
    """
    return {
        "chain": build_chain_from_module_names(module_names, graph),
        "extra_firsts": [],
        "extra_lasts": [],
    }


def get_line_numbers(
    importer: str, imported: str, graph: grimp.ImportGraph
) -> tuple[int | None, ...]:
    details = graph.get_import_details(importer=importer, imported=imported)
    line_numbers = tuple(i["line_number"] for i in details) if details else (None,)
    return line_numbers

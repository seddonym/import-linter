"""
Helper functions used by more than one contract type.

Code in here should not be relied upon as a public API; if you're
relying on it for a custom contract type, be aware things may change
without warning.
"""

from __future__ import annotations

import itertools
from typing import List, Optional, Sequence, Tuple, Union

import grimp
from grimp import ImportGraph
from typing_extensions import TypedDict

from importlinter.application import output
from importlinter.domain.imports import Module


class Link(TypedDict):
    importer: str
    imported: str
    # If the graph has been built manually, we may not know the line number.
    line_numbers: Tuple[Optional[int], ...]


Chain = List[Link]


class DetailedChain(TypedDict):
    chain: Chain
    extra_firsts: List[Link]
    extra_lasts: List[Link]


def render_chain_data(chain_data: DetailedChain) -> None:
    main_chain = chain_data["chain"]
    _render_direct_import(main_chain[0], extra_firsts=chain_data["extra_firsts"], first_line=True)

    for direct_import in main_chain[1:-1]:
        _render_direct_import(direct_import)

    if len(main_chain) > 1:
        _render_direct_import(main_chain[-1], extra_lasts=chain_data["extra_lasts"])


def find_segments(
    graph: ImportGraph, reference_graph: ImportGraph, importer: Module, imported: Module
) -> List[Chain]:
    """
    Return list of headless and tailless chains.

    Two graphs are passed in: the first is mutated, the second is used purely as a reference to
    look up import details which are otherwise removed during mutation.
    """
    segments = []
    for chain in _pop_shortest_chains(graph, importer=importer.name, imported=imported.name):
        if len(chain) == 2:
            raise ValueError("Direct chain found - these should have been removed.")
        segment: List[Link] = []
        for importer_in_chain, imported_in_chain in [
            (chain[i], chain[i + 1]) for i in range(len(chain) - 1)
        ]:
            import_details = reference_graph.get_import_details(
                importer=importer_in_chain, imported=imported_in_chain
            )
            line_numbers = tuple(sorted(set(j["line_number"] for j in import_details)))
            segment.append(
                {
                    "importer": importer_in_chain,
                    "imported": imported_in_chain,
                    "line_numbers": line_numbers,
                }
            )
        segments.append(segment)
    return segments


def segments_to_collapsed_chains(
    graph: ImportGraph, segments: List[Chain], importer: Module, imported: Module
) -> List[DetailedChain]:
    collapsed_chains: List[DetailedChain] = []
    for segment in segments:
        head_imports: List[Link] = []
        imported_module = segment[0]["imported"]
        candidate_modules = sorted(graph.find_modules_that_directly_import(imported_module))
        for module in [
            m
            for m in candidate_modules
            if Module(m) == importer or Module(m).is_descendant_of(importer)
        ]:
            import_details_list = graph.get_import_details(
                importer=module, imported=imported_module
            )
            line_numbers = tuple(sorted(set(j["line_number"] for j in import_details_list)))
            head_imports.append(
                {"importer": module, "imported": imported_module, "line_numbers": line_numbers}
            )

        tail_imports: List[Link] = []
        importer_module = segment[-1]["importer"]
        candidate_modules = sorted(graph.find_modules_directly_imported_by(importer_module))
        for module in [
            m
            for m in candidate_modules
            if Module(m) == imported or Module(m).is_descendant_of(imported)
        ]:
            import_details_list = graph.get_import_details(
                importer=importer_module, imported=module
            )
            line_numbers = tuple(sorted(set(j["line_number"] for j in import_details_list)))
            tail_imports.append(
                {"importer": importer_module, "imported": module, "line_numbers": line_numbers}
            )

        collapsed_chains.append(
            {
                "chain": [head_imports[0]] + segment[1:-1] + [tail_imports[0]],
                "extra_firsts": head_imports[1:],
                "extra_lasts": tail_imports[1:],
            }
        )

    return collapsed_chains


def _pop_shortest_chains(graph: ImportGraph, importer: str, imported: str):
    chain: Union[Optional[Tuple[str, ...]], bool] = True
    while chain:
        chain = graph.find_shortest_chain(importer, imported)
        if chain:
            # Remove chain of imports from graph.
            for index in range(len(chain) - 1):
                graph.remove_import(importer=chain[index], imported=chain[index + 1])
            yield chain


def format_line_numbers(line_numbers: Sequence[Optional[int]]) -> str:
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
    extra_firsts: Optional[List] = None,
    extra_lasts: Optional[List] = None,
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
    chain_as_links: Chain = [
        {
            "importer": importer,
            "imported": imported,
            "line_numbers": get_line_numbers(importer=importer, imported=imported, graph=graph),
        }
        for importer, imported in pairwise(chain_as_strings)
    ]
    return {
        "chain": chain_as_links,
        "extra_firsts": extra_firsts,
        "extra_lasts": extra_lasts,
    }


def get_line_numbers(
    importer: str, imported: str, graph: grimp.ImportGraph
) -> tuple[int | None, ...]:
    details = graph.get_import_details(importer=importer, imported=imported)
    line_numbers = tuple(i["line_number"] for i in details) if details else (None,)
    return line_numbers


def pairwise(iterable):
    """
    Return successive overlapping pairs taken from the input iterable.
    pairwise('ABCDEFG') --> AB BC CD DE EF FG

    TODO: Replace with itertools.pairwise once on Python 3.10.
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

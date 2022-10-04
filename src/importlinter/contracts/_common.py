"""
Helper functions used by more than one contract type.

Code in here should not be relied upon as a public API; if you're
relying on it for a custom contract type, be aware things may change
without warning.
"""

from typing import List, Optional, Tuple, Union, cast

from typing_extensions import TypedDict

from importlinter.application import output
from importlinter.domain.imports import Module
from importlinter.domain.ports.graph import ImportGraph


class Link(TypedDict):
    importer: str
    imported: str
    line_numbers: Tuple[int, ...]


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
            line_numbers = tuple(sorted(set(cast(int, j["line_number"]) for j in import_details)))
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
            line_numbers = tuple(
                sorted(set(cast(int, j["line_number"]) for j in import_details_list))
            )
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
            line_numbers = tuple(
                sorted(set(cast(int, j["line_number"]) for j in import_details_list))
            )
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
            line_numbers = ", ".join(f"l.{n}" for n in source["line_numbers"])
            import_strings.append(f"{prefix}{importer} ({line_numbers})")
        importer, imported = extra_firsts[-1]["importer"], extra_firsts[-1]["imported"]
        line_numbers = ", ".join(f"l.{n}" for n in extra_firsts[-1]["line_numbers"])
        import_strings.append(f"& {importer} -> {imported} ({line_numbers})")
    else:
        importer, imported = direct_import["importer"], direct_import["imported"]
        line_numbers = ", ".join(f"l.{n}" for n in direct_import["line_numbers"])
        import_strings.append(f"{importer} -> {imported} ({line_numbers})")

    if extra_lasts:
        indent_string = (len(direct_import["importer"]) + 4) * " "
        for destination in extra_lasts:
            imported = destination["imported"]
            line_numbers = ", ".join(f"l.{n}" for n in destination["line_numbers"])
            import_strings.append(f"{indent_string}& {imported} ({line_numbers})")

    for position, import_string in enumerate(import_strings):
        if first_line and position == 0:
            output.print_error(f"- {import_string}", bold=False)
        else:
            output.print_error(f"  {import_string}", bold=False)

from typing import List, Optional, Tuple

from typing_extensions import TypedDict

from importlinter.application import output


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

from importlinter.domain.contract import Contract, ContractCheck

from . import output
from .ports.reporting import Report

TEXT_LOGO = """
╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘
"""
BRAND_COLOR = "pale_turquoise1"
BRAND_COLOR = "#007575"

# Public functions
# ----------------


def print_title() -> None:
    if output.console.encoding.startswith("utf"):
        output.print(TEXT_LOGO, color=BRAND_COLOR)
    else:
        # The logo contains characters that can't be encoded in some encodings (e.g. cp1252).
        # Fall back to a simpler heading.
        output.print_heading("Import Linter", output.HEADING_LEVEL_ONE)


def render_report(report: Report) -> None:
    """
    Output the supplied report to the console.
    """
    if report.could_not_run:
        _render_could_not_run(report)
        return

    if report.show_timings:
        output.print(f"Building graph took {format_duration(report.graph_building_duration)}.")
        output.new_line()

    output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    output.print_heading(
        f"Analyzed {file_count} files, {dependency_count} dependencies.",
        output.HEADING_LEVEL_THREE,
    )

    for contract, contract_check in report.get_contracts_and_checks():
        duration = report.get_duration(contract) if report.show_timings else None
        render_contract_result_line(contract, contract_check, duration=duration)

    output.new_line()

    output.print(f"Contracts: {report.kept_count} kept, {report.broken_count} broken.")

    if report.warnings_count:
        output.new_line()
        _render_warnings(report)

    if report.broken_count:
        output.new_line()
        output.new_line()
        _render_broken_contracts_details(report)


def render_contract_result_line(
    contract: Contract, contract_check: ContractCheck, duration: int | None
) -> None:
    """
    Render the one-line contract check result.

    Args:
        ...
        duration: The contract check duration in milliseconds (optional).
                  The duration will only be displayed if it is provided.
    """
    result_text = "KEPT" if contract_check.kept else "BROKEN"
    warning_text = _build_warning_text(warnings_count=len(contract_check.warnings))
    color_key = output.SUCCESS if contract_check.kept else output.ERROR
    color = output.COLORS[color_key]
    output.print(f"{contract.name} ", newline=False)
    output.print(result_text, color=color, newline=False)
    output.print(warning_text, color=output.COLORS[output.WARNING], newline=False)
    if duration is not None:
        output.print(f" [{format_duration(duration)}]", newline=False)
    output.new_line()


def render_exception(exception: Exception) -> None:
    """
    Render any exception to the console.
    """
    output.print_error(str(exception))


# Private functions
# -----------------


def _render_could_not_run(report: Report) -> None:
    for contract_name, exception in report.invalid_contract_options.items():
        output.print_error(f'Contract "{contract_name}" is not configured correctly:')
        for field_name, message in exception.errors.items():
            output.indent_cursor()
            output.print_error(f"{field_name}: {message}", bold=False)


def _build_warning_text(warnings_count: int) -> str:
    if warnings_count:
        noun = "warning" if warnings_count == 1 else "warnings"
        return f" ({warnings_count} {noun})"
    else:
        return ""


def _render_warnings(report: Report) -> None:
    output.print_heading("Warnings", output.HEADING_LEVEL_TWO, style=output.WARNING)
    no_contract_outputted_yet = True

    for contract, check in report.get_contracts_and_checks():
        if check.warnings:
            if no_contract_outputted_yet:
                no_contract_outputted_yet = False
            else:
                output.new_line()
            output.print_heading(contract.name, output.HEADING_LEVEL_THREE, style=output.WARNING)
            for warning in check.warnings:
                output.print_warning(f"- {warning}")


def _render_broken_contracts_details(report: Report) -> None:
    output.print_heading("Broken contracts", output.HEADING_LEVEL_TWO, style=output.ERROR)

    for contract, check in report.get_contracts_and_checks():
        if check.kept:
            continue
        output.print_heading(contract.name, output.HEADING_LEVEL_THREE, style=output.ERROR)

        contract.render_broken_contract(check)


def format_duration(milliseconds: int) -> str:
    """
    Format a duration in milliseconds with units always in seconds:
    - < 1s: to three decimal places, e.g. 0.127s
    - < 10s: to one decimal place, e.g. 5.9s, 3.0s
    - >= 10s: to 0 decimal places, e.g. 10s, 132s
    """
    try:
        ms = int(milliseconds)
    except Exception:
        return f"{milliseconds}ms"

    s = ms / 1000.0
    if s < 1:
        return f"{s:.3f}s"
    if s < 10:
        return f"{s:.1f}s"
    return f"{int(round(s))}s"


def render_layers_diagram(layers: list[str], contract_name: str = "Layers") -> None:
    """
    Render an ASCII diagram of the layered architecture.

    Args:
        layers: List of layer names from highest to lowest.
        contract_name: Name of the contract to display.
    """
    if not layers:
        output.new_line()
        output.print("📭 No layers defined in this contract.", bold=True)
        output.new_line()
        output.print("To define layers, add a layers contract to your config:", color="#888888")
        output.new_line()
        output.console.print("  [#a7d8de]\\[importlinter:contract:my_layers][/#a7d8de]")
        output.print("  name = My Layered Architecture", color="#a7d8de")
        output.print("  type = layers", color="#a7d8de")
        output.print("  layers =", color="#a7d8de")
        output.print("      high_level", color="#a7d8de")
        output.print("      mid_level", color="#a7d8de")
        output.print("      low_level", color="#a7d8de")
        output.new_line()
        output.print(
            "See: https://import-linter.readthedocs.io/en/stable/contract_types/layers/",
            color="#888888",
        )
        output.new_line()
        return

    # Track if we have multi-module layers for the legend
    has_independent = any(" | " in layer for layer in layers)
    has_non_independent = any(" : " in layer for layer in layers)

    # Calculate box width based on longest layer name
    max_len = max(len(layer) for layer in layers)
    box_width = max(max_len + 8, 30)
    inner_width = box_width - 2

    output.new_line()
    output.print_heading(contract_name, output.HEADING_LEVEL_TWO)

    # Top of diagram with arrow
    output.print("        ▲ higher level (can import from layers below)")
    output.print("        │", color="#555555")

    # Top border
    output.print(f"   ┌{'─' * inner_width}┐")

    # Layers
    for i, layer in enumerate(layers):
        color = output.LAYER_COLORS[i % len(output.LAYER_COLORS)]

        # Style the separators differently
        if " | " in layer:
            # Independent: use ║ double line
            styled_layer = layer.replace(" | ", "  ║  ")
        elif " : " in layer:
            # Non-independent: use ⋮ dots
            styled_layer = layer.replace(" : ", "  ⋮  ")
        else:
            styled_layer = layer

        padded_layer = styled_layer.center(inner_width)

        # Add arrow on left side
        if i == 0:
            output.print("   │", newline=False)
        else:
            output.print("  ↓│", newline=False, color="#555555")

        output.print(padded_layer, color=color, newline=False)
        output.print("│")

        # Separator between layers (except after last)
        if i < len(layers) - 1:
            output.print(f"   ├{'─' * inner_width}┤", color="#555555")

    # Bottom border
    output.print(f"   └{'─' * inner_width}┘")
    output.print("        │", color="#555555")
    output.print("        ▼ lower level (cannot import layers above)")

    output.new_line()

    # Legend for multi-module layers
    if has_independent or has_non_independent:
        output.print("  ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈", color="#555555")
        output.print("  Legend:", bold=True)
        if has_independent:
            output.print("    ║  independent modules (cannot import each other)", color="#888888")
        if has_non_independent:
            output.print("    ⋮  grouped modules (can import each other)", color="#888888")

    output.new_line()

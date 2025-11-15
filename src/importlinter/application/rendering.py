from rich import box

from importlinter.domain.contract import Contract, ContractCheck

from . import output
from .ports.reporting import Report
from rich.panel import Panel
from .output import console
from rich.console import Group

TEXT_LOGO = """
╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║╔══╦══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║║║║║╔╗║╔╗║╔╣║ ║║  ╠╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚══╣║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘
"""
TEXT_LOGO_ALT = """
╔══╗─────────▶╔╗ ╔╗      ╔╗◀───┐
╚╣╠╝◀─────┐  ╔╝╚╗║║────▶╔╝╚╗   │
 ║║   ╔══╦══╦╩╗╔╝║║  ╔╦═╩╗╔╝╔═╦══╗
 ║║╔══╣╔╗║╔╗║╔╣║ ║║ ╔╬╣╔╗║║ ║│║╔═╝
╔╣╠╣║║║╚╝║╚╝║║║╚╗║╚═╝║║║║║╚╗║═╣║
╚══╩╩╩╣╔═╩══╩╝╚═╝╚═══╩╩╝╚╩═╩╩═╩╝
  └──▶║║                    ▲ 
      ╚╝────────────────────┘
"""

TEXT_LOGO = TEXT_LOGO_ALT
BRAND_COLOR = "pale_turquoise1"

# Public functions
# ----------------


def render_report(report: Report) -> None:
    """
    Output the supplied report to the console.
    """
    if report.could_not_run:
        _render_could_not_run(report)
        return

    # if report.show_timings:
    #     output.print(f"Building graph took {format_duration(report.graph_building_duration)}.")
    #     output.new_line()

    # output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    # output.print_heading(
    #     f"Analyzed {file_count} files, {dependency_count} dependencies.",
    #     output.HEADING_LEVEL_THREE,
    # )
    from rich.table import Table

    contracts_string = "[bold]Contracts:[/bold]\n\n"
    table = Table(expand=True, show_edge=False, style="dim", box=box.SIMPLE, title_style="")
    table.add_column("Contract")
    table.add_column("Kept", justify="left")
    table.add_column("Took", justify="right")

    for contract, contract_check in report.get_contracts_and_checks():
        duration = report.get_duration(contract) if report.show_timings else None
        rendered_line = render_contract_result_line_alt(
            contract, contract_check, duration=duration
        )
        contracts_string += f":play_button: {rendered_line}"
        result_text = ":white_check_mark:" if contract_check.kept else ":x:"
        color_key = output.SUCCESS if contract_check.kept else output.ERROR
        color = output.COLORS[color_key]
        rendered_result = f"[{color}]{result_text}[/{color}]"
        table.add_row(
            f"[italic][{color}]{contract.name}",
            rendered_result,
            f"[cyan]{format_duration(duration)}",
        )

    # output.new_line()

    # output.print(f"Contracts: {report.kept_count} kept, {report.broken_count} broken.")

    if report.warnings_count:
        output.new_line()
        _render_warnings(report)

    if report.broken_count:
        output.new_line()
        output.new_line()
        _render_broken_contracts_details(report)

    # Fake
    report_text = (
        f"\n\n:brick: Building graph took [cyan]{format_duration(report.graph_building_duration)}[/cyan].\n"
        f":face_with_monocle: Analyzed [cyan]{file_count}[/cyan] files, [cyan]{dependency_count}[/cyan] dependencies.\n"
        f":scroll: Contracts: [green]{report.kept_count} kept[/green], [red]{report.broken_count} broken[/red].\n"
    )

    group = Group("\n", table, report_text)
    report_panel = Panel(group, title=":page_facing_up: [bold] Summary")
    console.print(report_panel)


def render_contract_result_line_alt(
    contract: Contract, contract_check: ContractCheck, duration: int | None
) -> str:
    """
    Return the one-line contract check result as a string.

    Args:
        ...
        duration: The contract check duration in milliseconds (optional).
                  The duration will only be displayed if it is provided.
    """
    result_text = "KEPT" if contract_check.kept else "BROKEN"
    warning_text = _build_warning_text(warnings_count=len(contract_check.warnings))
    color_key = output.SUCCESS if contract_check.kept else output.ERROR
    color = output.COLORS[color_key]
    rendered = f"{contract.name} "
    rendered += f"[{color}]{result_text}[/{color}]"
    # TODO warning
    # output.print(warning_text, color=output.COLORS[output.WARNING], newline=False)
    if duration is not None:
        rendered += f" [{format_duration(duration)}]"
        # output.print(f" [{format_duration(duration)}]", newline=False)
    rendered += "\n"
    return rendered


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
    # Faked

    titles_by_string = {
        "Contract one": """
Here's some error.
        """,
        "Contract two": """
Another error.
""",
    }
    for title, message in titles_by_string.items():
        panel = Panel(message, title=f":x: [bold]{title}", style="red")
        console.print(panel)
    # output.print_heading("Broken contracts", output.HEADING_LEVEL_TWO, style=output.ERROR)
    #
    # for contract, check in report.get_contracts_and_checks():
    #     if check.kept:
    #         continue
    #     output.print_heading(contract.name, output.HEADING_LEVEL_THREE, style=output.ERROR)
    #
    #     contract.render_broken_contract(check)


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

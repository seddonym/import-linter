from importlinter.domain.contract import Contract, ContractCheck

from . import output
from .ports.reporting import Report

# Public functions
# ----------------
from rich.panel import Panel


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

    # output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    report_text = (
        f"Analyzed {file_count} files, {dependency_count} dependencies.\n"
        f"Contracts: {report.kept_count} kept, {report.broken_count} broken.\n"
    )

    # output.print_heading(
    #     f"Analyzed {file_count} files, {dependency_count} dependencies.",
    #     output.HEADING_LEVEL_THREE,
    # )
    from rich import print as rprint
    from rich.console import Group

    # tree = Tree("[bold]Contracts[/bold]")
    # tree.add("[italic]Contract one[/italic] [green]KEPT")
    # tree.add("[italic]Contract two[/italic] [red]BROKEN")
    # tree.add("[italic]Contract three[/italic] [green]KEPT")

    tree = """
[bold]Contracts[/bold]

:play_button: [italic]Contract one[/italic] [green]KEPT[/green]
:play_button: [italic]Contract two[/italic] [red]BROKEN[/red]
:play_button: [italic]Contract three[/italic] [green]KEPT[/green]
"""

    group = Group(report_text, tree)
    report_panel = Panel(group, title="Summary")

    for contract_name, error_report in _fake_error_reports():
        broken_panel = Panel(error_report, title=contract_name, style="red bold")
        rprint(broken_panel)
    # for contract, contract_check in report.get_contracts_and_checks():
    #     duration = report.get_duration(contract) if report.show_timings else None
    #     render_contract_result_line(contract, contract_check, duration=duration)

    output.new_line()

    # output.print(f"[bold]Contracts[/bold] {report.kept_count} kept, {report.broken_count} broken.")

    if report.warnings_count:
        output.new_line()
        _render_warnings(report)

    if report.broken_count:
        output.new_line()
        output.new_line()
        _render_broken_contracts_details(report)
    rprint(report_panel)


def _fake_error_reports():
    yield (
        "Layered contract",
        """
mypackage.low is not allowed to import mypackage.high:

- mypackage.low.blue -> mypackage.high.yellow (l.6)

- mypackage.low.green -> mypackage.high.blue (l.12)

- mypackage.low.blue (l.8, l.16)
  & mypackage.low.purple (l.11)
  & mypackage.low.white -> mypackage.utils.red (l.1)
  mypackage.utils.red -> mypackage.utils.yellow (l.2)
  mypackage.utils.yellow -> mypackage.utils.brown (l.?)
  mypackage.utils.brown -> mypackage.high.green (l.3)
                           & mypackage.high.black (l.11)
                           & mypackage.high.white (l.8, l.16)

- mypackage.low.purple -> mypackage.utils.yellow (l.9)
  mypackage.utils.yellow -> mypackage.utils.brown (l.?)


mypackage.low is not allowed to import mypackage.medium:

- mypackage.low.blue -> mypackage.medium.yellow (l.6)


mypackage.medium is not allowed to import mypackage.high:

- mypackage.medium.blue (l.8)
  & mypackage.medium.white -> mypackage.utils.yellow (l.1, l.10)
  mypackage.utils.yellow -> mypackage.utils.brown (l.?)
  mypackage.utils.brown -> mypackage.high.green (l.3)
                           & mypackage.high.black (l.11)


The following modules are not listed as layers:

- mypackage.brown
- mypackage.green
- mypackage.purple

(Since this contract is marked as 'exhaustive', every child of every container
must be declared as a layer.)
    """,
    )
    yield (
        "Forbidden contract",
        """
mypackage.two is not allowed to import mypackage.purple:

-   mypackage.two -> mypackage.utils (l.9)
    mypackage.utils -> mypackage.purple (l.1)


mypackage.three is not allowed to import mypackage.green:

-   mypackage.three -> mypackage.green (l.4)


        """,
    )


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

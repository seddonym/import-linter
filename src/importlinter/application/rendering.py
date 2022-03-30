from . import output
from .ports.reporting import Report

# Public functions
# ----------------


def render_report(report: Report) -> None:
    """
    Output the supplied report to the console.
    """
    if report.could_not_run:
        _render_could_not_run(report)
        return

    output.print_heading("Import Linter", output.HEADING_LEVEL_ONE)

    if report.show_timings:
        output.print(f"Building graph took {report.graph_building_duration}s.")
        output.new_line()

    output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    output.print_heading(
        f"Analyzed {file_count} files, {dependency_count} dependencies.",
        output.HEADING_LEVEL_THREE,
    )

    for contract, contract_check in report.get_contracts_and_checks():
        result_text = "KEPT" if contract_check.kept else "BROKEN"
        warning_text = _build_warning_text(warnings_count=len(contract_check.warnings))
        color_key = output.SUCCESS if contract_check.kept else output.ERROR
        color = output.COLORS[color_key]
        output.print(f"{contract.name} ", newline=False)
        output.print(result_text, color=color, newline=False)
        output.print(warning_text, color=output.COLORS[output.WARNING], newline=False)
        if report.show_timings:
            output.print(f" [{report.get_duration(contract)}s]", newline=False)
        output.new_line()

    output.new_line()

    output.print(f"Contracts: {report.kept_count} kept, {report.broken_count} broken.")

    if report.warnings_count:
        output.new_line()
        _render_warnings(report)

    if report.broken_count:
        output.new_line()
        output.new_line()
        _render_broken_contracts_details(report)


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

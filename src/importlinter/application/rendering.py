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
    output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    output.print_heading(
        f"Analyzed {file_count} files, {dependency_count} dependencies.",
        output.HEADING_LEVEL_THREE,
    )

    for contract, contract_check in report.get_contracts_and_checks():
        result_text = "KEPT" if contract_check.kept else "BROKEN"
        color_key = output.SUCCESS if contract_check.kept else output.ERROR
        color = output.COLORS[color_key]
        output.print(f"{contract.name} ", newline=False)
        output.print(result_text, color=color)
    output.new_line()

    output.print(f"Contracts: {report.kept_count} kept, {report.broken_count} broken.")

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


def _render_broken_contracts_details(report: Report) -> None:
    output.print_heading("Broken contracts", output.HEADING_LEVEL_TWO, style=output.ERROR)

    for contract, check in report.get_contracts_and_checks():
        if check.kept:
            continue
        output.print_heading(contract.name, output.HEADING_LEVEL_THREE, style=output.ERROR)

        contract.render_broken_contract(check)

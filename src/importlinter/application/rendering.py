from .ports.reporting import Report
from . import output


def render_report(report: Report) -> None:
    output.print_heading("Import Linter", output.HEADING_LEVEL_ONE)
    output.print_heading("Contracts", output.HEADING_LEVEL_TWO)
    file_count = report.module_count
    dependency_count = report.import_count
    output.print_heading(
        f"Analyzed {file_count} files, {dependency_count} dependencies.",
        output.HEADING_LEVEL_THREE)

    for contract, contract_check in report.get_contracts_and_checks():
        result_text = 'KEPT' if contract_check.kept else 'BROKEN'
        output.print(f"{contract.name} {result_text}")
    output.new_line()

    output.print(f"Contracts: {report.kept_count} kept, {report.broken_count} broken.")

    if report.broken_count:
        output.new_line()
        output.new_line()
        _render_broken_contracts_details(report)


def _render_broken_contracts_details(report: Report) -> None:
    output.print_heading('Broken contracts', output.HEADING_LEVEL_TWO, style=output.ERROR)

    for contract, check in report.get_contracts_and_checks():
        if check.kept:
            continue
        output.print_heading(contract.name, output.HEADING_LEVEL_THREE, style=output.ERROR)

        contract.render_broken_contract(check)


# def print_contract_one_liner(printer, contract: Contract) -> None:
#     is_kept = contract.is_kept
#     printer.print('{} '.format(contract), newline=False)
#     # if contract.whitelisted_paths:
#     #     printer.print('({} whitelisted paths) '.format(len(contract.whitelisted_paths)),
#     #                 newline=False)
#     status_map = {
#         True: ('KEPT', SUCCESS),
#         False: ('BROKEN', ERROR),
#     }
#     color = COLORS[status_map[is_kept][1]]
#     printer.print(status_map[is_kept][0], color=color, bold=True)

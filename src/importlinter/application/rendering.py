from typing import Optional

from .ports.reporting import Report
from .ports.printing import Printer


def render_report(report: Report, printer: Printer) -> None:
    _print_heading(printer, "Import Linter", HEADING_LEVEL_ONE)
    _print_heading(printer, "Contracts", HEADING_LEVEL_TWO)
    _print_heading(printer, "Analyzed 23 files, 44 dependencies.", HEADING_LEVEL_THREE)

    printer.print("Contract foo KEPT")
    printer.print("Contract bar KEPT")
    _new_line(printer)

    printer.print("Contracts: 2 kept, 0 broken.")


ERROR = 'error'
SUCCESS = 'success'
COLORS = {
    ERROR: 'red',
    SUCCESS: 'green',
}

HEADING_LEVEL_ONE = 1
HEADING_LEVEL_TWO = 2
HEADING_LEVEL_THREE = 3

HEADING_MAP = {
    HEADING_LEVEL_ONE: ('=', True),
    HEADING_LEVEL_TWO: ('-', True),
    HEADING_LEVEL_THREE: ('-', False),
}

INDENT_SIZE = 4


def _print_heading(
    printer: Printer,
    text: str,
    level: int,
    style: Optional[str] = None,
) -> None:
    """
    Prints the supplied text to the console, formatted as a heading.

    Args:
        text (str): the text to format as a heading.
        level (int): the level of heading to display (one of the keys of HEADING_MAP).
        style (str, optional): ERROR or SUCCESS style to apply (default None).
    Usage:

        ClickPrinter.print_heading('Foo', ClickPrinter.HEADING_LEVEL_ONE)
    """
    # Setup styling variables.
    is_bold = True
    color = COLORS[style] if style else None
    line_char, show_line_above = HEADING_MAP[level]
    heading_line = line_char * len(text)

    # Print lines.
    if show_line_above:
        printer.print(heading_line, bold=is_bold, color=color)
    printer.print(text, bold=is_bold, color=color)
    printer.print(heading_line, bold=is_bold, color=color)
    printer.print()


def _print_success(printer, text, bold=True):
    """
    Prints a line to the console, formatted as a success.
    """
    printer.print(text, color=COLORS[SUCCESS], bold=bold)


def _print_error(printer, text, bold=True):
    """
    Prints a line to the console, formatted as an error.
    """
    printer.print(text, color=COLORS[ERROR], bold=bold)


def _indent_cursor(printer):
    """
    Indents the cursor ready to print a line.
    """
    printer.print(' ' * INDENT_SIZE, newline=False)


def _new_line(printer):
    printer.print()


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

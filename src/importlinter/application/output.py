from typing import Optional

from .ports.printing import Printer
from .app_config import settings


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


class Output:
    def print(
        self,
        text: str = '',
        bold: bool = False,
        color: Optional[str] = None,
        newline: bool = True
    ):
        self.printer.print(text, bold, color, newline)

    def indent_cursor(self):
        """
        Indents the cursor ready to print a line.
        """
        self.printer.print(' ' * INDENT_SIZE, newline=False)

    def new_line(self):
        self.printer.print()

    def print_heading(
        self,
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
            self.printer.print(heading_line, bold=is_bold, color=color)
        self.printer.print(text, bold=is_bold, color=color)
        self.printer.print(heading_line, bold=is_bold, color=color)
        self.printer.print()

    def print_success(self, text, bold=True):
        """
        Prints a line to the console, formatted as a success.
        """
        self.printer.print(text, color=COLORS[SUCCESS], bold=bold)

    def print_error(self, text, bold=True):
        """
        Prints a line to the console, formatted as an error.
        """
        self.printer.print(text, color=COLORS[ERROR], bold=bold)

    @property
    def printer(self) -> Printer:
        return settings.PRINTER


# Use prebound method pattern to provide a simple API.
# https://python-patterns.guide/python/prebound-methods/
_instance = Output()
print = _instance.print
indent_cursor = _instance.indent_cursor
new_line = _instance.new_line
print_success = _instance.print_success
print_heading = _instance.print_heading
print_error = _instance.print_error

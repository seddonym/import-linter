from typing import Optional

from .app_config import settings
from .ports.printing import Printer

ERROR = "error"
SUCCESS = "success"
COLORS = {ERROR: "red", SUCCESS: "green"}

HEADING_LEVEL_ONE = 1
HEADING_LEVEL_TWO = 2
HEADING_LEVEL_THREE = 3

HEADING_MAP = {
    HEADING_LEVEL_ONE: ("=", True),
    HEADING_LEVEL_TWO: ("-", True),
    HEADING_LEVEL_THREE: ("-", False),
}

INDENT_SIZE = 4


class Output:
    """
    A class for writing output to the console.

    This should always be used instead of the built in print function, as it uses the Printer
    port. This makes it easier for tests to swap in a different Printer so we can more easily
    assert what would be written to the console.
    """

    def print(
        self, text: str = "", bold: bool = False, color: Optional[str] = None, newline: bool = True
    ) -> None:
        """
        Print a line.

        Args:
            text (str):               The text to print.
            bold (bool, optional):    Whether to style the text in bold. (Default False.)
            color (str, optional):    The color of text to use. One of the values of the
                                      COLORS dictionary.
            newline (bool, optional): Whether to include a new line after the text.
                                      (Default True.)
        """
        self.printer.print(text, bold, color, newline)

    def indent_cursor(self):
        """
        Indents the cursor ready to print a line.
        """
        self.printer.print(" " * INDENT_SIZE, newline=False)

    def new_line(self):
        """
        Print a blank line.
        """
        self.printer.print()

    def print_heading(self, text: str, level: int, style: Optional[str] = None) -> None:
        """
        Prints the supplied text to the console, formatted as a heading.

        Args:
            text (str):            The text to format as a heading.
            level (int):           The level of heading to display (one of the keys
                                   of HEADING_MAP).
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

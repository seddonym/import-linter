from rich.console import Console


ERROR = "error"
SUCCESS = "success"
WARNING = "warning"
COLORS = {ERROR: "red", SUCCESS: "green", WARNING: "yellow"}

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
    """

    def print(
        self,
        text: str = "",
        bold: bool = False,
        color: str | None = None,
        newline: bool = True,
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
        printer.print(text, bold, color, newline)

    def indent_cursor(self) -> None:
        """
        Indents the cursor ready to print a line.
        """
        printer.print(" " * INDENT_SIZE, newline=False)

    def new_line(self) -> None:
        """
        Print a blank line.
        """
        printer.print()

    def print_heading(self, text: str, level: int, style: str | None = None) -> None:
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
            printer.print(heading_line, bold=is_bold, color=color)
        printer.print(text, bold=is_bold, color=color)
        printer.print(heading_line, bold=is_bold, color=color)
        printer.print()

    def print_success(self, text: str, bold: bool = True) -> None:
        """
        Prints a line to the console, formatted as a success.
        """
        printer.print(text, color=COLORS[SUCCESS], bold=bold)

    def print_error(self, text: str, bold: bool = True) -> None:
        """
        Prints a line to the console, formatted as an error.
        """
        printer.print(text, color=COLORS[ERROR], bold=bold)

    def print_warning(self, text: str) -> None:
        """
        Prints a line to the console, formatted as a warning.
        """
        printer.print(text, color=COLORS[WARNING])


# Use prebound method pattern to provide a simple API.
# https://python-patterns.guide/python/prebound-methods/
_instance = Output()
print = _instance.print
indent_cursor = _instance.indent_cursor
new_line = _instance.new_line
print_success = _instance.print_success
print_heading = _instance.print_heading
print_error = _instance.print_error
print_warning = _instance.print_warning


def verbose_print(
    verbose: bool,
    text: str = "",
    bold: bool = False,
    color: str | None = None,
    newline: bool = True,
) -> None:
    """
    Print a message, but only if we're in verbose mode.
    """
    if verbose:
        printer.print(text, bold, color, newline)


class RichPrinter:
    def print(
        self,
        text: str = "",
        bold: bool = False,
        color: str | None = None,
        newline: bool = True,
    ) -> None:
        adjusted_text = text
        if color:
            adjusted_text = f"[{color}]{text}[/{color}]"
        if bold:
            adjusted_text = f"[bold]{text}[/bold]"
        end = "\n" if newline else ""
        console.print(adjusted_text, end=end)


printer = RichPrinter()
console = Console(highlight=False)

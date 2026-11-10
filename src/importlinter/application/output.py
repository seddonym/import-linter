from rich.console import Console, JustifyMethod
from collections.abc import Iterable
from rich.table import Table


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


console = Console(highlight=False)


class Output:
    """
    A class for writing output to the console.

    Output provides a few convenience methods for printing.

    For finer-grained control or more advanced user interface features,
    use the Rich Console object instantiated in this module (importlinter.application.output.console).
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
        adjusted_text = text
        if color:
            adjusted_text = f"[{color}]{text}[/{color}]"
        if bold:
            adjusted_text = f"[bold]{text}[/bold]"
        end = "\n" if newline else ""
        console.print(adjusted_text, end=end)

    def indent_cursor(self) -> None:
        """
        Indents the cursor ready to print a line.
        """
        console.print(" " * INDENT_SIZE, end="")

    def new_line(self) -> None:
        """
        Print a blank line.
        """
        console.print()

    def print_heading(self, text: str, level: int, style: str | None = None) -> None:
        """
        Prints the supplied text to the console, formatted as a heading.

        Args:
            text (str):            The text to format as a heading.
            level (int):           The level of heading to display (one of the keys
                                   of HEADING_MAP).
            style (str, optional): ERROR or SUCCESS style to apply (default None).
        Usage:

            output.print_heading('Foo', output.HEADING_LEVEL_ONE)
        """
        # Setup styling variables.
        is_bold = True
        color = COLORS[style] if style else None
        line_char, show_line_above = HEADING_MAP[level]
        heading_line = line_char * len(text)

        # Print lines.
        if show_line_above:
            self.print(heading_line, bold=is_bold, color=color)
        self.print(text, bold=is_bold, color=color)
        self.print(heading_line, bold=is_bold, color=color)
        self.print()

    def print_success(self, text: str, bold: bool = True) -> None:
        """
        Prints a line to the console, formatted as a success.
        """
        self.print(text, color=COLORS[SUCCESS], bold=bold)

    def print_error(self, text: str, bold: bool = True) -> None:
        """
        Prints a line to the console, formatted as an error.
        """
        self.print(text, color=COLORS[ERROR], bold=bold)

    def print_warning(self, text: str) -> None:
        """
        Prints a line to the console, formatted as a warning.
        """
        self.print(text, color=COLORS[WARNING])

    def print_table(
        self,
        columns: Iterable[str],
        rows: Iterable[Iterable[str]],
        footer: Iterable[str] | None = None,
        column_justify: Iterable[JustifyMethod] | None = None,
    ) -> None:
        """
        Prints a table to the console.

        Args:
            columns:        The column headings.
            rows:           The rows of the table, each a list of values corresponding to the
                             columns.
            footer:         An optional final row, visually separated from the rows above it.
            column_justify: An optional justification ("left", "center" or "right") for each
                             column, corresponding to columns. Defaults to left-justified.
        """
        table = Table()
        justifications = list(column_justify) if column_justify is not None else []
        for index, column in enumerate(columns):
            justify = justifications[index] if index < len(justifications) else "left"
            table.add_column(column, justify=justify)
        rows = list(rows)
        last_index = len(rows) - 1
        for index, row in enumerate(rows):
            table.add_row(*row, end_section=footer is not None and index == last_index)
        if footer is not None:
            table.add_row(*footer, style="bold")
        console.print(table)


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
print_table = _instance.print_table


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
        print(text, bold, color, newline)

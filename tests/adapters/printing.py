import textwrap

from importlinter.application.ports.printing import Printer


class FakePrinter(Printer):
    def __init__(self) -> None:
        self._buffer = ""

    def print(
        self,
        text: str = "",
        bold: bool = False,
        color: str | None = None,
        newline: bool = True,
    ) -> None:
        """
        Prints a line.
        """
        self._buffer += text
        if newline:
            self._buffer += "\n"

    def pop_and_assert(self, expected_string):
        """
        Assert that the string is what is in the buffer, removing it from the buffer.

        To aid with readable test assertions, the expected string will have leading and trailing
        lines removed, and the whole thing will be dedented, before comparison.
        """

        modified_expected_string = textwrap.dedent(expected_string.strip("\n"))

        popped_string = self._buffer
        self._buffer = ""

        assert popped_string == modified_expected_string

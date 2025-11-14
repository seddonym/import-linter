import textwrap

from importlinter.adapters.printing import RichPrinter, console


class FakePrinter(RichPrinter):
    def __init__(self) -> None:
        self._buffer = ""

    def print(self, *args, **kwargs) -> None:
        with console.capture() as capture:
            super().print(*args, **kwargs)
        self._buffer += capture.get()

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

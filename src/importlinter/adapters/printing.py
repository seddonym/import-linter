from importlinter.application.ports.printing import Printer
from rich import text as rtext
from importlinter.application import output


class RichPrinter(Printer):
    """
    Console printer that uses Rich.
    """

    def print(
        self,
        text: str = "",
        bold: bool = False,
        color: str | None = None,
        newline: bool = True,
        as_log: bool = False,
    ) -> None:
        print_ = output.console.log if as_log else output.console.print
        styles = []
        if bold:
            styles.append("bold")
        if color:
            styles.append(color)
        print_(rtext.Text(text, style=" ".join(styles)), end=("\n" if newline else ""))

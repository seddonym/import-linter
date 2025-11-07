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
    ) -> None:
        styles = []
        if bold:
            styles.append("bold")
        if color:
            styles.append(color)
        output.console.print(
            rtext.Text(text, style=" ".join(styles)), end=("\n" if newline else "")
        )

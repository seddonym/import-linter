from importlinter.application.ports.printing import Printer
from rich.console import Console


class RichPrinter(Printer):
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


console = Console(highlight=False)

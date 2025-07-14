from typing import Optional

import click

from importlinter.application.ports.printing import Printer


class ClickPrinter(Printer):
    """
    Console printer that uses Click's formatting helpers.
    """

    def print(
        self, text: str = "", bold: bool = False, color: Optional[str] = None, newline: bool = True
    ) -> None:
        # click.secho(text, bold=bold, fg=color, nl=newline)
        # A tricky solution to gh-267
        # Remove when click reaches v9.0.0
        print(click.style(text, bold=bold, fg=color), end=("\n" if newline else ""))

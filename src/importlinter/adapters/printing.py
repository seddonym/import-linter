from typing import Optional

from importlinter.application.ports.printing import Printer


class ClickPrinter(Printer):
    def print(
            self,
            text: str = '',
            bold: bool = False,
            color: Optional[str] = None,
            newline: bool = True
    ) -> None:
        raise NotImplementedError

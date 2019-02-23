from importlinter.application.ports.printing import Printer
from importlinter.application.ports.reporting import Report


class ConsolePrinter(Printer):
    def print(self, report: Report) -> None:
        raise NotImplementedError

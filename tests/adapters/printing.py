from importlinter.application.ports.printing import Printer

from importlinter.application.ports.reporting import Report


class FakePrinter(Printer):
    def print(self, report: Report) -> None:
        pass

    def pop_and_assert(self, string):
        pass

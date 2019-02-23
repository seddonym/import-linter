from importlinter.application.ports.printing import Printer


class ConsolePrinter(Printer):
    def print(self, string: str) -> None:
        raise NotImplementedError

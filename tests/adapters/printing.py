from importlinter.application.ports.printing import Printer


class FakePrinter(Printer):
    def pop_and_assert(self, string):
        pass

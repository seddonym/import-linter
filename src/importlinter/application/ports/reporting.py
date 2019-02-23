from importlinter.domain.ports.graph import ImportGraph


class Reporter:
    ...


class ExceptionReporter:
    ...


class Report:
    def __init__(self, graph: ImportGraph) -> None:
        self.graph = graph
        self.contains_failures = False

import abc
from typing import List, Optional

from importlinter.domain.ports.graph import ImportGraph


class SourceSyntaxError(Exception):
    """
    Indicates a syntax error in the code being statically analysed to build the graph.
    """

    def __init__(self, filename: str, lineno: Optional[int], text: Optional[str]) -> None:
        """
        Args:
            filename: The file which contained the error.
            lineno: The line number containing the error.
            text: The text containing the error.
        """
        self.filename = filename
        self.lineno = lineno
        self.text = text

    def __str__(self):
        lineno = self.lineno or "?"
        text = self.text or "<unavailable>"
        return f"Syntax error in {self.filename}, line {lineno}: {text}"

    def __eq__(self, other):
        return (self.filename, self.lineno, self.text) == (
            other.filename,
            other.lineno,
            other.text,
        )


class GraphBuilder(abc.ABC):
    @abc.abstractmethod
    def build(
        self, root_package_names: List[str], include_external_packages: bool = False
    ) -> ImportGraph:
        """
        Raises:
            SourceSyntaxError if the code under analysis contains a syntax error.
        """
        raise NotImplementedError

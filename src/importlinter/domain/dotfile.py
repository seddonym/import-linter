from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    destination: str
    label: str = ""
    emphasized: bool = False

    def __str__(self) -> str:
        return f'"{DotGraph.render_module(self.source)}" ->  "{DotGraph.render_module(self.destination)}"{self._render_attrs()}'

    def _render_attrs(self) -> str:
        attrs: dict[str, str] = {}
        if self.label:
            attrs["label"] = self.label
        if self.emphasized:
            attrs["style"] = "dashed"
        if attrs:
            joined_attrs = ", ".join([f'{key}="{value}"' for key, value in attrs.items()])
            return f" [{joined_attrs}]"
        else:
            return ""


@dataclass
class DotGraph:
    """
    A directed graph that can be rendered in DOT format.

    https://en.wikipedia.org/wiki/DOT_(graph_description_language)
    """

    title: str
    concentrate: bool = True
    nodes: set[str] = field(default_factory=set)
    edges: set[Edge] = field(default_factory=set)

    def add_node(self, name: str) -> None:
        self.nodes.add(name)

    def add_edge(self, edge: Edge) -> None:
        self.edges.add(edge)

    def render(self) -> str:
        # concentrate=true means that we merge the lines together.
        indent = "    "
        lines = ["digraph {", f"{indent}node [fontname=helvetica]"]
        if self.concentrate:
            lines.append(f"{indent}concentrate=true")
        for node in sorted(self.nodes):
            lines.append(f'{indent}"{self.render_module(node)}"')
        for edge in sorted(self.edges):
            lines.append(f"{indent}{edge}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def render_module(module: str) -> str:
        # Render as relative module.
        return f".{module.split('.')[-1]}"

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    destination: str
    label: str = ""
    emphasized: bool = False

    def __str__(self) -> str:
        return self.render(base_module="")

    def render(self, base_module: str) -> str:
        return f'"{DotGraph.render_module(self.source, base_module)}" ->  "{DotGraph.render_module(self.destination, base_module)}"{self._render_attrs()}'

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
    depth: int = 1
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
            lines.append(f'{indent}"{self.render_module(node, self.title)}"')
        for edge in sorted(self.edges):
            lines.append(f"{indent}{edge.render(self.title)}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def render_module(module: str, base_module: str = "") -> str:
        # Render as relative module by stripping the base module prefix.
        if base_module and module.startswith(base_module + "."):
            relative = module[len(base_module) :]
            return relative  # Already starts with "."
        else:
            # Fallback: show as relative with just the last component.
            return f".{module.split('.')[-1]}"

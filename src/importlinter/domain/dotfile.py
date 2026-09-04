from dataclasses import dataclass, field, fields
from enum import Enum


class EdgeStyle(str, Enum):
    SOLID = "solid"
    DASHED = "dashed"


class EdgeArrowhead(str, Enum):
    NORMAL = "normal"
    VEE = "vee"


@dataclass(frozen=True, order=True)
class Edge:
    source: str
    destination: str
    label: str = ""
    style: EdgeStyle = EdgeStyle.SOLID
    arrowhead: EdgeArrowhead = EdgeArrowhead.NORMAL

    def __str__(self) -> str:
        return f'"{DotGraph.render_module(self.source)}" ->  "{DotGraph.render_module(self.destination)}"{self._render_attrs()}'

    def _render_attrs(self) -> str:
        attrs: dict[str, str] = {}
        if self.label:
            attrs["label"] = self.label

        if self.style != _EDGE_FIELDS["style"].default:
            attrs["style"] = self.style.value

        if self.arrowhead != _EDGE_FIELDS["arrowhead"].default:
            attrs["arrowhead"] = self.arrowhead.value

        if attrs:
            joined_attrs = ", ".join([f'{key}="{value}"' for key, value in attrs.items()])
            return f" [{joined_attrs}]"
        else:
            return ""


_EDGE_FIELDS = {f.name: f for f in fields(Edge)}


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
    node_labels: dict[str, str] = field(default_factory=dict)

    def add_node(self, name: str, label: str = "") -> None:
        self.nodes.add(name)
        if label:
            self.node_labels[name] = label

    def add_edge(self, edge: Edge) -> None:
        self.edges.add(edge)

    def render(self) -> str:
        # concentrate=true means that we merge the lines together.
        indent = "    "
        lines = ["digraph {", f"{indent}node [fontname=helvetica]"]
        if self.concentrate:
            lines.append(f"{indent}concentrate=true")
        for node in sorted(self.nodes):
            rendered = self.render_module(node)
            if node in self.node_labels:
                lines.append(f'{indent}"{rendered}" [label="{self.node_labels[node]}"]')
            else:
                lines.append(f'{indent}"{rendered}"')
        for edge in sorted(self.edges):
            lines.append(f"{indent}{edge}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def render_module(module: str) -> str:
        # Render as relative module.
        return f".{module.split('.')[-1]}"

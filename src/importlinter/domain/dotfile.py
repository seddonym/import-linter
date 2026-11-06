from collections.abc import Callable
from dataclasses import dataclass, field, fields
from enum import StrEnum


class EdgeStyle(StrEnum):
    SOLID = "solid"
    DASHED = "dashed"


class EdgeArrowhead(StrEnum):
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
        return self.render(DotGraph.render_module)

    def render(self, render_id: Callable[[str], str]) -> str:
        return (
            f'"{render_id(self.source)}" ->  "{render_id(self.destination)}"{self._render_attrs()}'
        )

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
    # When True, node identifiers are rendered relative to a shared parent (e.g. ".blue"), which
    # is only unambiguous when every node has the same parent. When False (e.g. for a top-level
    # overview of several packages), the fully qualified module name is used as the identifier so
    # that modules with different parents don't collide.
    relative: bool = True

    def add_node(self, name: str, label: str = "") -> None:
        self.nodes.add(name)
        if label:
            self.node_labels[name] = label

    def add_edge(self, edge: Edge) -> None:
        self.edges.add(edge)

    def render(self) -> str:
        # concentrate=true means that we merge the lines together.
        indent = "    "
        render_id = self._render_node_id
        lines = ["digraph {", f"{indent}node [fontname=helvetica]"]
        if self.concentrate:
            lines.append(f"{indent}concentrate=true")
        for node in sorted(self.nodes):
            rendered = render_id(node)
            if node in self.node_labels:
                lines.append(f'{indent}"{rendered}" [label="{self.node_labels[node]}"]')
            else:
                lines.append(f'{indent}"{rendered}"')
        for edge in sorted(self.edges):
            lines.append(f"{indent}{edge.render(render_id)}")
        lines.append("}")
        return "\n".join(lines) + "\n"

    def _render_node_id(self, module: str) -> str:
        # In relative mode, every node shares a parent, so the last component is a unique
        # identifier. In non-relative mode (a top-level overview), nodes may have different
        # parents, so the fully qualified name is needed to keep identifiers unique.
        if self.relative:
            return self.render_module(module)
        return module

    @staticmethod
    def render_module(module: str) -> str:
        # Render as relative module, except for root packages, which have no parent to be
        # relative to.
        last_part = module.split(".")[-1]
        if "." in module:
            return f".{last_part}"
        return last_part

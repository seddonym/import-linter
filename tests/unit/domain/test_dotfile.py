from textwrap import dedent
from importlinter.domain.dotfile import DotGraph, Edge, EdgeArrowhead, EdgeStyle


class TestDotGraph:
    def test_render_empty_graph(self):
        dot = DotGraph(title="mypackage")
        rendered = dot.render()
        assert "digraph" in rendered
        assert "concentrate=true" in rendered

    def test_concentrate_false(self):
        dot = DotGraph(title="mypackage", concentrate=False)
        rendered = dot.render()
        assert "concentrate=true" not in rendered

    def test_render_with_nodes_and_edges(self):
        dot = DotGraph(title="mypackage.foo")
        dot.add_node("mypackage.foo.bar")
        dot.add_node("mypackage.foo.baz")
        dot.add_edge(Edge(source="mypackage.foo.bar", destination="mypackage.foo.baz"))

        rendered = dot.render()

        assert rendered == dedent("""\
            digraph {
                node [fontname=helvetica]
                concentrate=true
                ".bar"
                ".baz"
                ".bar" ->  ".baz"
            }
        """)

    def test_render_vee_arrowhead(self):
        edge = Edge(
            source="mypackage.foo.bar",
            destination="mypackage.foo.baz",
            arrowhead=EdgeArrowhead.VEE,
        )

        assert str(edge) == '".bar" ->  ".baz" [arrowhead="vee"]'

    def test_render_combined_style_and_arrowhead(self):
        # A cycle breaker (dashed) that is also lazy (open arrowhead) composes both attributes.
        edge = Edge(
            source="mypackage.foo.bar",
            destination="mypackage.foo.baz",
            style=EdgeStyle.DASHED,
            arrowhead=EdgeArrowhead.VEE,
        )

        assert str(edge) == '".bar" ->  ".baz" [style="dashed", arrowhead="vee"]'

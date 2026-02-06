from textwrap import dedent
from importlinter.domain.dotfile import DotGraph, Edge


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

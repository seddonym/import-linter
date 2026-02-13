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

    def test_render_with_depth_2(self):
        dot = DotGraph(title="mypackage.foo", depth=2)
        dot.add_node("mypackage.foo.blue")
        dot.add_node("mypackage.foo.green")
        dot.add_node("mypackage.foo.blue.alpha")
        dot.add_edge(Edge(source="mypackage.foo.blue.alpha", destination="mypackage.foo.green"))

        rendered = dot.render()

        assert rendered == dedent("""\
            digraph {
                node [fontname=helvetica]
                concentrate=true
                ".blue"
                ".blue.alpha"
                ".green"
                ".blue.alpha" ->  ".green"
            }
        """)


class TestRenderModule:
    def test_render_module_with_base_module(self):
        assert DotGraph.render_module("mypackage.foo.bar", "mypackage.foo") == ".bar"

    def test_render_module_with_nested_base_module(self):
        assert DotGraph.render_module("mypackage.foo.blue.alpha", "mypackage.foo") == ".blue.alpha"

    def test_render_module_without_base_module(self):
        assert DotGraph.render_module("mypackage.foo.bar") == ".bar"

    def test_render_module_fallback_when_no_prefix_match(self):
        assert DotGraph.render_module("other.bar", "mypackage.foo") == ".bar"


class TestEdge:
    def test_render_with_base_module(self):
        edge = Edge(source="mypackage.foo.bar", destination="mypackage.foo.baz")
        rendered = edge.render("mypackage.foo")
        assert rendered == '".bar" ->  ".baz"'

    def test_render_with_depth_2_modules(self):
        edge = Edge(source="mypackage.foo.blue.alpha", destination="mypackage.foo.green")
        rendered = edge.render("mypackage.foo")
        assert rendered == '".blue.alpha" ->  ".green"'

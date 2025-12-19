import pytest

from importlinter.application import rendering
from importlinter.application.output import console


@pytest.mark.parametrize(
    "milliseconds, expected",
    [
        (0, "0.000s"),
        (1, "0.001s"),
        (532, "0.532s"),
        (999, "0.999s"),
        (1000, "1.0s"),
        (1234, "1.2s"),
        (9950, "9.9s"),
        (9999, "10.0s"),  # a bit ugly but not really worth fixing
        (10000, "10s"),
        (12400, "12s"),
    ],
)
def test_format_duration(milliseconds, expected):
    assert rendering.format_duration(milliseconds) == expected


class TestRenderLayersDiagram:
    def test_renders_single_layer(self):
        with console.capture() as capture:
            rendering.render_layers_diagram(["domain"], "My Contract")

        output = capture.get()
        assert "My Contract" in output
        assert "domain" in output
        assert "higher level" in output
        assert "lower level" in output

    def test_renders_multiple_layers(self):
        layers = ["cli", "api", "domain"]

        with console.capture() as capture:
            rendering.render_layers_diagram(layers, "Layered Architecture")

        output = capture.get()
        assert "Layered Architecture" in output
        assert "cli" in output
        assert "api" in output
        assert "domain" in output

    def test_renders_independent_modules_with_legend(self):
        layers = ["presentation", "business | service", "data"]

        with console.capture() as capture:
            rendering.render_layers_diagram(layers, "Test Contract")

        output = capture.get()
        assert "business" in output
        assert "service" in output
        assert "Legend:" in output
        assert "independent modules" in output

    def test_renders_grouped_modules_with_legend(self):
        layers = ["presentation", "business : service", "data"]

        with console.capture() as capture:
            rendering.render_layers_diagram(layers, "Test Contract")

        output = capture.get()
        assert "business" in output
        assert "service" in output
        assert "Legend:" in output
        assert "grouped modules" in output

    def test_no_legend_for_simple_layers(self):
        layers = ["cli", "api", "domain"]

        with console.capture() as capture:
            rendering.render_layers_diagram(layers, "Simple Contract")

        output = capture.get()
        assert "Legend:" not in output

    def test_empty_layers_shows_helpful_message(self):
        with console.capture() as capture:
            rendering.render_layers_diagram([], "Empty Contract")

        output = capture.get()
        assert "No layers defined" in output
        assert "importlinter:contract:my_layers" in output
        assert "https://import-linter.readthedocs.io" in output

    def test_uses_default_contract_name(self):
        with console.capture() as capture:
            rendering.render_layers_diagram(["layer1", "layer2"])

        output = capture.get()
        assert "Layers" in output

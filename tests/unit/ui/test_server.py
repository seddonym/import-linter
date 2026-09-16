import pytest


MODULE_NAME = "mypackage"


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from importlinter.ui.server import create_app

    app = create_app(root_packages=[MODULE_NAME], initial_module=MODULE_NAME)
    return TestClient(app)


class TestIndex:
    def test_returns_html_with_module_name(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "Import Linter" in response.text
        assert "mypackage" in response.text


class TestGetGraph:
    def test_passes_settings_through_to_generate_dot(self, client, monkeypatch):
        from importlinter.ui import server
        from importlinter.ui.explorer import ModuleDot

        calls = {}

        def fake_generate_dot(
            cache,
            module,
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
            root_packages,
        ):
            calls["show_lazy_imports"] = show_lazy_imports
            calls["show_cycle_breakers"] = show_cycle_breakers
            calls["root_packages"] = root_packages
            return ModuleDot(dot_string="digraph {}", module=module, child_packages=set())

        monkeypatch.setattr(server, "generate_dot", fake_generate_dot)

        response = client.get("/api/graph/mypackage?show_lazy_imports=true")

        assert response.status_code == 200
        assert calls["show_lazy_imports"] is True
        assert calls["show_cycle_breakers"] is False
        assert calls["root_packages"] == [MODULE_NAME]

    def test_overview_route_passes_empty_module(self, client, monkeypatch):
        from importlinter.ui import server
        from importlinter.ui.explorer import ModuleDot

        calls = {}

        def fake_generate_dot(
            cache,
            module,
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
            root_packages,
        ):
            calls["module"] = module
            return ModuleDot(dot_string="digraph {}", module=module, child_packages=set())

        monkeypatch.setattr(server, "generate_dot", fake_generate_dot)

        response = client.get("/api/graph")

        assert response.status_code == 200
        assert calls["module"] == ""

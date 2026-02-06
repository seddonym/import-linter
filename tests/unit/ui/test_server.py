import pytest
from fastapi.testclient import TestClient

from importlinter.ui.server import create_app

MODULE_NAME = "mypackage"


@pytest.fixture
def client() -> TestClient:
    app = create_app(module_name=MODULE_NAME)
    return TestClient(app)


class TestIndex:
    def test_returns_html_with_module_name(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert "Import Linter" in response.text
        assert "mypackage" in response.text

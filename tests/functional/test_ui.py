import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from importlinter.ui.server import create_app

this_directory = Path(__file__).parent
assets_directory = this_directory / ".." / "assets"
testpackage_directory = assets_directory / "testpackage"


def test_starts_without_error():
    process = subprocess.Popen(
        ["import-linter", "explore", "testpackage"],
        stderr=subprocess.PIPE,
        cwd=testpackage_directory,
        env={**os.environ, "BROWSER": "echo"},
    )
    try:
        for line in process.stderr:
            if b"Application startup complete" in line:
                return
        assert False, "UI did not start"
    finally:
        process.terminate()
        process.wait()


def test_exits_with_error_if_module_not_importable():
    result = subprocess.run(
        ["import-linter", "explore", "nonexistent"],
        capture_output=True,
    )
    assert result.returncode == 1
    assert b"Could not import 'nonexistent'" in result.stderr


class TestDrawGraph:
    def test_outputs_dot_to_stdout(self):
        result = subprocess.run(
            ["import-linter", "drawgraph", "testpackage"],
            capture_output=True,
            cwd=testpackage_directory,
        )
        assert result.returncode == 0
        output = result.stdout.decode()
        assert output.startswith("digraph {")
        assert ".high" in output
        assert ".low" in output

    def test_exits_with_error_if_module_not_importable(self):
        result = subprocess.run(
            ["import-linter", "drawgraph", "nonexistent"],
            capture_output=True,
        )
        assert result.returncode == 1
        assert b"Could not import" in result.stderr


class TestGraphApi:
    @pytest.fixture(autouse=True)
    def setup_sys_path(self):
        sys.path.insert(0, str(testpackage_directory))
        yield
        sys.path.remove(str(testpackage_directory))

    @pytest.fixture
    def client(self):
        return TestClient(create_app(module_name="testpackage"))

    def test_returns_graph_for_top_level_module(self, client):
        response = client.get("/api/graph/testpackage")
        assert response.status_code == 200
        data = response.json()
        assert data["module"] == "testpackage"
        assert "digraph" in data["dot_string"]

    def test_identifies_child_packages(self, client):
        response = client.get("/api/graph/testpackage")
        data = response.json()
        # testpackage has sub-packages: high, indirect, low, medium
        # utils is a leaf module, not a package
        assert ".high" in data["child_packages"]
        assert ".low" in data["child_packages"]
        assert ".medium" in data["child_packages"]
        assert ".indirect" in data["child_packages"]
        assert ".utils" not in data["child_packages"]

    def test_drills_into_subpackage(self, client):
        response = client.get("/api/graph/testpackage.high")
        data = response.json()
        assert data["module"] == "testpackage.high"
        # high has sub-package blue and leaf green
        assert ".blue" in data["child_packages"]
        assert ".green" not in data["child_packages"]

    def test_caches_grimp_graph(self, client):
        # Two requests for different sub-modules of same top-level package
        # should both succeed (verifies caching doesn't break things)
        r1 = client.get("/api/graph/testpackage")
        r2 = client.get("/api/graph/testpackage.high")
        assert r1.status_code == 200
        assert r2.status_code == 200

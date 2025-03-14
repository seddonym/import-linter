from pathlib import Path

import pytest

import importlinter
from importlinter import api
import importlinter.adapters
import importlinter.adapters.filesystem


@pytest.mark.parametrize(
    "config_directory, config_file, expected",
    (
        (
            "testpackage",
            "setup.cfg",
            dict(
                session_options={"root_packages": ["testpackage"]},
                contracts_options=[
                    {
                        "name": "Test independence contract",
                        "id": "test-independence",
                        "type": "independence",
                        "modules": [
                            "testpackage.high.blue",
                            "testpackage.high.green",
                        ],
                        "ignore_imports": [
                            "testpackage.utils -> testpackage.high.green",
                            "testpackage.*.blue.* -> testpackage.indirect.*",
                        ],
                    }
                ],
            ),
        ),
        (
            "multipleroots",
            ".multiplerootskeptcontract.ini",
            dict(
                session_options={"root_packages": ["rootpackageblue", "rootpackagegreen"]},
                contracts_options=[
                    {
                        "name": "Multiple roots kept contract",
                        "id": "multiple-roots",
                        "type": "forbidden",
                        "source_modules": "rootpackageblue.one.alpha",
                        "forbidden_modules": "rootpackagegreen.two",
                    }
                ],
            ),
        ),
    ),
)
def test_read_config(config_directory, config_file, expected):
    this_directory = Path(__file__).parent
    config_filename = str(this_directory / ".." / "assets" / config_directory / config_file)

    result = api.read_configuration(config_filename)

    assert result == expected


@pytest.mark.parametrize(
    "default_encoding",
    (
        "cp1252",
        "UTF-8",
    ),
)
def test_read_config_unicode(default_encoding, monkeypatch):
    this_directory = Path(__file__).parent
    config_directory = "testpackage"
    config_file = ".unicode.toml"
    config_filename = str(this_directory / ".." / "assets" / config_directory / config_file)

    def mock_read(self, file_name, encoding) -> str:
        with open(file_name, encoding=encoding or default_encoding) as file:
            return file.read()

    monkeypatch.setattr(importlinter.adapters.filesystem.FileSystem, "read", mock_read)

    config_result = api.read_configuration(config_filename)
    result = config_result["contracts_options"][0]["name"]

    expected = "Cönträct tö tést µnícðde pœrs€ng"

    assert result == expected

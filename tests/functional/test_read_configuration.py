from pathlib import Path

import pytest

from importlinter import api


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

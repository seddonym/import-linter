import os
import tempfile
from pathlib import Path

from importlinter import cli

this_directory = Path(__file__).parent
assets_directory = this_directory / ".." / "assets"

testpackage_directory = assets_directory / "testpackage"


class TestCaching:
    def test_no_cache(self):
        os.chdir(testpackage_directory)

        with tempfile.TemporaryDirectory() as cache_dir:
            cli.lint_imports(cache_dir=cache_dir, no_cache=True)

            meta_file = Path(cache_dir) / "testpackage.meta.json"
            data_file = Path(cache_dir) / "dGVzdHBhY2thZ2U-.data.json"

            assert not meta_file.exists()
            assert not data_file.exists()

    def test_supplied_cache_dir(self):
        os.chdir(testpackage_directory)

        with tempfile.TemporaryDirectory() as cache_dir:
            cli.lint_imports(cache_dir=cache_dir, is_debug_mode=True)

            meta_file = Path(cache_dir) / "testpackage.meta.json"
            data_file = Path(cache_dir) / "dGVzdHBhY2thZ2U-.data.json"

            assert meta_file.exists()
            assert data_file.exists()

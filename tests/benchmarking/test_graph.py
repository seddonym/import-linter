from __future__ import annotations

import pytest
from grimp import ImportGraph

from . import graph as fake_graph


def _count_imports(graph: ImportGraph, importer: str, imported: str) -> int:
    return len(graph.find_matching_direct_imports(f"{importer}.** -> {imported}.**"))


class TestBuildGraph:
    @pytest.mark.parametrize(
        "importer, imported, expected_count",
        [
            ("mypkg.domain", "mypkg.data", 10000),
            ("mypkg.application", "mypkg.domain", 10000),
            ("mypkg.plugins.red", "mypkg.domain", 5000),
            ("mypkg.plugins.green", "mypkg.domain", 5000),
            ("mypkg.plugins.blue", "mypkg.domain", 5000),
            ("mypkg.plugins.red", "mypkg.application", 5000),
            ("mypkg.plugins.green", "mypkg.application", 5000),
            ("mypkg.plugins.blue", "mypkg.application", 5000),
            # Nothing imports the higher layers.
            ("mypkg.data", "mypkg.domain", 0),
            ("mypkg.domain", "mypkg.application", 0),
            ("mypkg.data", "mypkg.application", 0),
            ("mypkg.data", "mypkg.plugins", 0),
            ("mypkg.domain", "mypkg.plugins", 0),
            ("mypkg.application", "mypkg.plugins", 0),
            # The plugins don't import each other.
            ("mypkg.plugins.red", "mypkg.plugins.green", 0),
            ("mypkg.plugins.green", "mypkg.plugins.blue", 0),
            ("mypkg.plugins.blue", "mypkg.plugins.red", 0),
        ],
    )
    def test_imports_between_layers(self, importer, imported, expected_count):
        graph = fake_graph.build_graph()

        assert _count_imports(graph, importer, imported) == expected_count

    def test_has_no_other_imports(self):
        graph = fake_graph.build_graph()

        assert graph.count_imports() == 10000 + 10000 + 3 * (5000 + 5000)

    def test_has_modules_in_each_layer(self):
        graph = fake_graph.build_graph()

        for layer in fake_graph._LAYERS:
            assert len(graph.find_children(f"mypkg.{layer}")) == 1000
            assert graph.find_children(f"mypkg.{layer}") == {
                f"mypkg.{layer}.{number:03d}" for number in range(1000)
            }

    def test_is_the_same_every_time(self):
        first = fake_graph.build_graph()
        second = fake_graph.build_graph()

        assert first.find_matching_direct_imports(
            "mypkg.** -> mypkg.**"
        ) == second.find_matching_direct_imports("mypkg.** -> mypkg.**")


class TestAddImports:
    def test_adds_imports_of_the_imported_layer_by_the_importer_layer(self):
        graph = fake_graph.build_graph()

        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=10)

        assert _count_imports(graph, "mypkg.data", "mypkg.domain") == 10
        # The other imports are not affected.
        assert _count_imports(graph, "mypkg.domain", "mypkg.data") == 10000
        assert graph.count_imports() == 50000 + 10

    def test_can_add_imports_between_other_layers(self):
        graph = fake_graph.build_graph()

        fake_graph.add_imports(
            graph, importer_layer="plugins.red", imported_layer="plugins.green", count=7
        )

        assert _count_imports(graph, "mypkg.plugins.red", "mypkg.plugins.green") == 7
        assert graph.count_imports() == 50000 + 7

    def test_adds_more_imports_each_time(self):
        graph = fake_graph.build_graph()

        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=10)
        fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=5)

        assert _count_imports(graph, "mypkg.data", "mypkg.domain") == 15

    def test_adds_imports_that_are_not_already_in_the_graph(self):
        graph = fake_graph.build_graph()
        assert _count_imports(graph, "mypkg.domain", "mypkg.data") == 10000

        fake_graph.add_imports(graph, importer_layer="domain", imported_layer="data", count=10)

        assert _count_imports(graph, "mypkg.domain", "mypkg.data") == 10010

    def test_raises_if_there_are_not_enough_imports_possible(self, monkeypatch):
        graph = fake_graph.build_graph()
        # Only allow a few imports, so we don't have to go through every possible import.
        monkeypatch.setattr(fake_graph, "_IMPORT_ORDER", [(0, 0), (0, 1), (1, 0)])

        with pytest.raises(ValueError, match="only 3 are possible"):
            fake_graph.add_imports(graph, importer_layer="data", imported_layer="domain", count=4)

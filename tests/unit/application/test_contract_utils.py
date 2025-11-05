import pytest
from grimp import ImportGraph

from importlinter.application.contract_utils import AlertLevel, remove_ignored_imports
from importlinter.domain.helpers import MissingImport
from importlinter.domain.imports import (
    DirectImport,
    ImportExpression,
    Module,
    ModuleExpression,
)


class TestRemoveIgnoredImports:
    DIRECT_IMPORTS = [
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.yellow"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.purple"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.blue"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(  # Direct Imports can appear twice, for different line numbers.
            importer=Module("mypackage.green"),
            imported=Module("mypackage.blue"),
            line_number=2,
            line_contents="-",
        ),
    ]

    @pytest.mark.parametrize("alert_level", [AlertLevel.NONE, AlertLevel.WARN, AlertLevel.ERROR])
    def test_no_unresolved_import_expressions(self, alert_level):
        graph = self._build_graph(self.DIRECT_IMPORTS)

        warnings = remove_ignored_imports(
            graph=graph,
            ignore_imports=[
                ImportExpression(
                    importer=ModuleExpression("mypackage.green"),
                    imported=ModuleExpression("mypackage.blue"),
                ),
                ImportExpression(
                    importer=ModuleExpression("mypackage.green"),
                    imported=ModuleExpression("mypackage.purple"),
                ),
            ],
            unmatched_alerting=alert_level,
        )

        assert graph.count_imports() == 1  # The three matching imports have been removed.
        assert warnings == []

    @pytest.mark.parametrize(
        "alert_level, expected_result",
        [
            (AlertLevel.NONE, []),
            (
                AlertLevel.WARN,
                [
                    "No matches for ignored import mypackage.* -> mypackage.nonexistent.",
                    "No matches for ignored import mypackage.nonexistent -> mypackage.blue.",
                ],
            ),
            (
                AlertLevel.ERROR,
                MissingImport(
                    "No matches for ignored import mypackage.* -> mypackage.nonexistent."
                ),
            ),
        ],
    )
    def test_unresolved_import_expressions(self, alert_level, expected_result):
        graph = self._build_graph(self.DIRECT_IMPORTS)
        ignore_imports = [
            ImportExpression(
                importer=ModuleExpression("mypackage.green"),
                imported=ModuleExpression("mypackage.blue"),
            ),
            ImportExpression(
                importer=ModuleExpression("mypackage.*"),
                imported=ModuleExpression("mypackage.nonexistent"),
            ),
            ImportExpression(
                importer=ModuleExpression("mypackage.green"),
                imported=ModuleExpression("mypackage.purple"),
            ),
            ImportExpression(
                importer=ModuleExpression("mypackage.nonexistent"),
                imported=ModuleExpression("mypackage.blue"),
            ),
        ]

        if isinstance(expected_result, Exception):
            with pytest.raises(type(expected_result), match=str(expected_result)):
                remove_ignored_imports(
                    graph=graph,
                    ignore_imports=ignore_imports,
                    unmatched_alerting=alert_level,
                )
        else:
            warnings = remove_ignored_imports(
                graph=graph,
                ignore_imports=ignore_imports,
                unmatched_alerting=alert_level,
            )
            assert graph.count_imports() == 1  # The three matching imports have been removed.
            assert set(warnings) == set(expected_result)

    def _build_graph(self, direct_imports):
        graph = ImportGraph()
        for direct_import in direct_imports:
            graph.add_import(
                importer=direct_import.importer.name,
                imported=direct_import.imported.name,
                line_number=direct_import.line_number,
                line_contents=direct_import.line_contents,
            )
        return graph

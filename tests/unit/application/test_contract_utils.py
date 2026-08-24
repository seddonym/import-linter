import pytest
from grimp import ImportGraph

from importlinter.application.contract_utils import (
    AlertLevel,
    remove_ignored_imports,
    remove_ignored_imports_and_report,
)
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
        ],
    )
    def test_unresolved_import_expressions_with_non_error_level_alerting(
        self, alert_level, expected_result
    ):
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

        warnings = remove_ignored_imports(
            graph=graph,
            ignore_imports=ignore_imports,
            unmatched_alerting=alert_level,
        )
        assert graph.count_imports() == 1  # The three matching imports have been removed.
        assert warnings == expected_result

    def test_unresolved_import_expressions_with_error_level_alerting(self):
        graph = self._build_graph(self.DIRECT_IMPORTS)

        expected_result = MissingImport(
            "No matches for ignored import mypackage.* -> mypackage.nonexistent.\n"
            "No matches for ignored import mypackage.nonexistent -> mypackage.blue."
        )

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

        with pytest.raises(MissingImport, match=str(expected_result)):
            remove_ignored_imports(
                graph=graph,
                ignore_imports=ignore_imports,
                unmatched_alerting=AlertLevel.ERROR,
            )

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


class TestRemoveIgnoredImportsAndReport:
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

        import_removal = remove_ignored_imports_and_report(
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
        assert import_removal.warnings == ()
        # Two distinct (importer, imported) pairs were removed (green->blue, green->purple),
        # even though green->blue accounted for two individual import statements.
        assert import_removal.ignored_import_count == 2
        assert import_removal.removed_imports == frozenset(
            {
                DirectImport(
                    importer=Module("mypackage.green"), imported=Module("mypackage.blue")
                ),
                DirectImport(
                    importer=Module("mypackage.green"), imported=Module("mypackage.purple")
                ),
            }
        )

    @pytest.mark.parametrize(
        "alert_level, expected_result",
        [
            (AlertLevel.NONE, ()),
            (
                AlertLevel.WARN,
                (
                    "No matches for ignored import mypackage.* -> mypackage.nonexistent.",
                    "No matches for ignored import mypackage.nonexistent -> mypackage.blue.",
                ),
            ),
        ],
    )
    def test_unresolved_import_expressions_with_non_error_level_alerting(
        self, alert_level, expected_result
    ):
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

        import_removal = remove_ignored_imports_and_report(
            graph=graph,
            ignore_imports=ignore_imports,
            unmatched_alerting=alert_level,
        )
        assert graph.count_imports() == 1  # The three matching imports have been removed.
        assert import_removal.warnings == expected_result
        # Two distinct (importer, imported) pairs were removed (green->blue, green->purple);
        # the two unresolved expressions don't contribute to the count.
        assert import_removal.ignored_import_count == 2

    def test_unresolved_import_expressions_with_error_level_alerting(self):
        graph = self._build_graph(self.DIRECT_IMPORTS)
        import_count_before = graph.count_imports()

        expected_result = MissingImport(
            "No matches for ignored import mypackage.* -> mypackage.nonexistent.\n"
            "No matches for ignored import mypackage.nonexistent -> mypackage.blue."
        )

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

        with pytest.raises(MissingImport, match=str(expected_result)):
            remove_ignored_imports_and_report(
                graph=graph,
                ignore_imports=ignore_imports,
                unmatched_alerting=AlertLevel.ERROR,
            )

        # Nothing should have been removed from the graph: an ERROR-level unmatched
        # expression aborts the whole operation before any removal happens.
        assert graph.count_imports() == import_count_before

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

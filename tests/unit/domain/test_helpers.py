import re
from typing import Dict, List, Union, cast

import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore

from importlinter.domain.helpers import (
    AlertingLevels,
    MissingImport,
    add_imports,
    import_expressions_to_imports,
    parse_unmatched_ignore_imports_alerting,
    pop_import_expressions,
    pop_imports,
)
from importlinter.domain.imports import DirectImport, ImportExpression, Module


class TestPopImports:
    IMPORTS = [
        dict(
            importer="mypackage.green",
            imported="mypackage.yellow",
            line_number=1,
            line_contents="blah",
        ),
        dict(
            importer="mypackage.green",
            imported="mypackage.blue",
            line_number=2,
            line_contents="blahblah",
        ),
        dict(
            importer="mypackage.blue",
            imported="mypackage.green",
            line_number=10,
            line_contents="blahblahblah",
        ),
    ]

    def test_succeeds(self):
        graph = self._build_graph(imports=self.IMPORTS)
        imports_to_pop = self.IMPORTS[0:2]
        import_to_leave = self.IMPORTS[2]

        result = pop_imports(
            graph,
            [
                DirectImport(importer=Module(i["importer"]), imported=Module(i["imported"]))
                for i in imports_to_pop
            ],
        )

        assert result == imports_to_pop
        assert graph.direct_import_exists(
            importer=import_to_leave["importer"], imported=import_to_leave["imported"]
        )
        assert graph.count_imports() == 1

    def test_raises_missing_import_if_module_not_found(self):
        graph = self._build_graph(imports=self.IMPORTS)
        non_existent_import = DirectImport(
            importer=Module("mypackage.nonexistent"),
            imported=Module("mypackage.yellow"),
            line_number=1,
            line_contents="-",
        )
        with pytest.raises(
            MissingImport,
            match=re.escape(
                "Ignored import mypackage.nonexistent -> mypackage.yellow "
                "not present in the graph."
            ),
        ):
            pop_imports(graph, [non_existent_import])

    def test_works_with_multiple_external_imports_from_same_module(self):
        imports_to_pop = [
            dict(
                importer="mypackage.green",
                imported="someexternalpackage",
                line_number=2,
                line_contents="from someexternalpackage import one",
            ),
            dict(
                importer="mypackage.green",
                imported="someexternalpackage",
                line_number=2,
                line_contents="from someexternalpackage import two",
            ),
        ]
        imports = self.IMPORTS + imports_to_pop
        graph = self._build_graph(imports=imports)

        result = pop_imports(
            graph,
            [
                DirectImport(
                    importer=Module(i["importer"]),
                    imported=Module(i["imported"]),
                    line_number=i["line_number"],
                    line_contents=i["line_contents"],
                )
                for i in imports_to_pop
            ],
        )

        assert result == imports_to_pop
        one_of_the_popped_imports = imports_to_pop[0]
        assert not graph.direct_import_exists(
            importer=one_of_the_popped_imports["importer"],
            imported=one_of_the_popped_imports["imported"],
        )
        assert graph.count_imports() == len(self.IMPORTS)

    def _build_graph(self, imports):
        graph = ImportGraph()
        for import_ in imports:
            graph.add_import(**import_)
        return graph


class TestImportExpressionsToImports:
    DIRECT_IMPORTS = [
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.yellow"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.blue"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.blue"),
            imported=Module("mypackage.green"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.blue.cats"),
            imported=Module("mypackage.purple.dogs"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green.cats"),
            imported=Module("mypackage.orange.dogs"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green.cats"),
            imported=Module("mypackage.orange.mice"),
            line_number=1,
            line_contents="-",
        ),
        # Direct imports of external packages can appear more than once, as the external package
        # is squashed.
        DirectImport(
            importer=Module("mypackage.brown"),
            imported=Module("someotherpackage"),
            line_number=1,
            line_contents="from someotherpackage import one",
        ),
        DirectImport(
            importer=Module("mypackage.brown"),
            imported=Module("someotherpackage"),
            line_number=2,
            line_contents="from someotherpackage import two",
        ),
    ]

    @pytest.mark.parametrize(
        "description, expressions, expected",
        [
            (
                "No wildcards",
                [
                    ImportExpression(
                        importer=DIRECT_IMPORTS[0].importer.name,
                        imported=DIRECT_IMPORTS[0].imported.name,
                    ),
                ],
                [DIRECT_IMPORTS[0]],
            ),
            (
                "Importer wildcard",
                [
                    ImportExpression(importer="mypackage.*", imported="mypackage.blue"),
                ],
                [DIRECT_IMPORTS[1]],
            ),
            (
                "Imported wildcard",
                [
                    ImportExpression(importer="mypackage.green", imported="mypackage.*"),
                ],
                DIRECT_IMPORTS[0:2],
            ),
            (
                "Importer and imported wildcards",
                [
                    ImportExpression(importer="mypackage.*", imported="mypackage.*"),
                ],
                DIRECT_IMPORTS[0:3],
            ),
            (
                "Inner wildcard",
                [
                    ImportExpression(importer="mypackage.*.cats", imported="mypackage.*.dogs"),
                ],
                DIRECT_IMPORTS[3:5],
            ),
            (
                "Multiple expressions, non-overlapping",
                [
                    ImportExpression(importer="mypackage.green", imported="mypackage.*"),
                    ImportExpression(
                        importer="mypackage.green.cats", imported="mypackage.orange.*"
                    ),
                ],
                DIRECT_IMPORTS[0:2] + DIRECT_IMPORTS[4:6],
            ),
            (
                "Multiple expressions, overlapping",
                [
                    ImportExpression(importer="mypackage.*", imported="mypackage.blue"),
                    ImportExpression(importer="mypackage.green", imported="mypackage.blue"),
                ],
                [DIRECT_IMPORTS[1]],
            ),
            (
                "Multiple imports of external package with same importer",
                [
                    ImportExpression(importer="mypackage.brown", imported="someotherpackage"),
                ],
                DIRECT_IMPORTS[6:8],
            ),
        ],
    )
    def test_succeeds(self, description, expressions, expected):
        graph = self._build_graph(self.DIRECT_IMPORTS)
        actual = sorted(
            import_expressions_to_imports(graph, expressions, AlertingLevels.ERROR),
            key=_direct_import_sort_key,
        )
        expected = sorted(expected, key=_direct_import_sort_key)

        assert actual == expected

    def test_raises_missing_import(self):
        graph = ImportGraph()
        graph.add_module("mypackage")
        graph.add_module("other")
        graph.add_import(
            importer="mypackage.b", imported="other.foo", line_number=1, line_contents="-"
        )

        expression = ImportExpression(importer="mypackage.a.*", imported="other.foo")

        with pytest.raises(MissingImport):
            import_expressions_to_imports(graph, [expression], AlertingLevels.ERROR)

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


class TestPopImportExpressions:
    DIRECT_IMPORTS = [
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.yellow"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green"),
            imported=Module("mypackage.blue"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.blue"),
            imported=Module("mypackage.green"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.blue.cats"),
            imported=Module("mypackage.purple.dogs"),
            line_number=1,
            line_contents="-",
        ),
        DirectImport(
            importer=Module("mypackage.green.cats"),
            imported=Module("mypackage.orange.dogs"),
            line_number=1,
            line_contents="-",
        ),
    ]

    def test_succeeds(self):
        graph = self._build_graph(self.DIRECT_IMPORTS)
        expressions = [
            ImportExpression(importer="mypackage.green", imported="mypackage.*"),
            # Expressions can overlap.
            ImportExpression(importer="mypackage.green", imported="mypackage.blue"),
            ImportExpression(importer="mypackage.blue.cats", imported="mypackage.purple.dogs"),
        ]

        popped_imports: List[Dict[str, Union[str, int]]] = pop_import_expressions(
            graph, expressions
        )

        # Cast to direct imports to make comparison easier.
        popped_direct_imports: List[DirectImport] = sorted(
            map(self._dict_to_direct_import, popped_imports), key=_direct_import_sort_key
        )
        expected = sorted(
            [
                self.DIRECT_IMPORTS[0],
                self.DIRECT_IMPORTS[1],
                self.DIRECT_IMPORTS[3],
            ],
            key=_direct_import_sort_key,
        )
        assert popped_direct_imports == expected
        assert graph.count_imports() == 2

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

    def _dict_to_direct_import(self, import_details: Dict[str, Union[str, int]]) -> DirectImport:
        return DirectImport(
            importer=Module(cast(str, import_details["importer"])),
            imported=Module(cast(str, import_details["imported"])),
            line_number=cast(int, import_details["line_number"]),
            line_contents=cast(str, import_details["line_contents"]),
        )


def test_add_imports():
    graph = ImportGraph()
    import_details = [
        {"importer": "a", "imported": "b", "line_number": 1, "line_contents": "lorem ipsum"},
        {"importer": "c", "imported": "d", "line_number": 2, "line_contents": "lorem ipsum 2"},
    ]
    assert not graph.modules
    add_imports(graph, import_details)
    assert graph.modules == {"a", "b", "c", "d"}


def _direct_import_sort_key(direct_import: DirectImport):
    # Doesn't matter how we sort, just a way of sorting consistently for comparison.
    return (
        direct_import.importer.name,
        direct_import.imported.name,
        direct_import.line_number,
    )


@pytest.mark.parametrize(
    "value, expected",
    [
        # values
        pytest.param("", AlertingLevels.ERROR),
        pytest.param("error", AlertingLevels.ERROR),
        pytest.param("warn", AlertingLevels.WARN),
        pytest.param("none", AlertingLevels.NONE),
        # trailing/leading spaces
        pytest.param(" ", AlertingLevels.ERROR),
        pytest.param(" none  ", AlertingLevels.NONE),
    ],
)
def test_parse_unmatched_ignore_imports_alerting(value: str, expected: AlertingLevels) -> None:
    actual = parse_unmatched_ignore_imports_alerting(value)

    assert actual == expected


def test_parse_unmatched_ignore_imports_alerting_raise_if_not_valid() -> None:
    value = "invalid"
    message = f"Invalid value `{value}` for unmatched_ignore_imports_alerting"

    with pytest.raises(ValueError, match=message):
        parse_unmatched_ignore_imports_alerting(value)

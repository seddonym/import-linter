import re
from typing import Dict, List, Union, cast

import pytest
from grimp.adaptors.graph import ImportGraph  # type: ignore

from importlinter.domain.helpers import (
    MissingImport,
    add_imports,
    import_expressions_to_imports,
    pop_import_expressions,
    pop_imports,
    pop_unresolved_import_expressions,
    unresolved_import_expressions_to_imports,
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

        assert sorted(
            import_expressions_to_imports(graph, expressions), key=_direct_import_sort_key
        ) == sorted(expected, key=_direct_import_sort_key)

    def test_raises_missing_import(self):
        graph = ImportGraph()
        graph.add_module("mypackage")
        graph.add_module("other")
        graph.add_import(
            importer="mypackage.b", imported="other.foo", line_number=1, line_contents="-"
        )

        expression = ImportExpression(importer="mypackage.a.*", imported="other.foo")
        with pytest.raises(MissingImport):
            import_expressions_to_imports(graph, [expression])

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


class TestUnresolvedImportExpressionsToImports:
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
    def test_succeeds(
        self, description: str, expressions: List[ImportExpression], expected: List[DirectImport]
    ):
        graph = self._build_graph(self.DIRECT_IMPORTS)

        actual = unresolved_import_expressions_to_imports(graph, expressions)
        actual_resolved_imports, acautl_unresolved_imports = actual

        assert acautl_unresolved_imports == []
        assert sorted(actual_resolved_imports, key=_direct_import_sort_key) == sorted(
            expected, key=_direct_import_sort_key
        )

    def test_returns_missing_import(self):
        graph = ImportGraph()
        graph.add_module("mypackage")
        graph.add_module("other")
        graph.add_import(
            importer="mypackage.b", imported="other.foo", line_number=1, line_contents="-"
        )

        expression = ImportExpression(importer="mypackage.a.*", imported="other.foo")

        actual = unresolved_import_expressions_to_imports(graph, [expression])
        expected = ([], [ImportExpression(imported="other.foo", importer="mypackage.a.*")])

        assert actual == expected

    # fixme: make a base class
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


class TestPopUnresolvedImportExpressions:
    # fixme: make shared class
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
            # Missing import
            ImportExpression(importer="mypackage.green", imported="mypackage.black.*"),
        ]

        # popped_imports: List[Dict[str, Union[str, int]]] = pop_unresolved_import_expressions(
        popped_imports = pop_unresolved_import_expressions(graph, expressions)

        popped_resolved_imports, popped_unresolved_imports = popped_imports

        # Cast to direct imports to make comparison easier.
        popped_direct_imports: List[DirectImport] = sorted(
            map(self._dict_to_direct_import, popped_resolved_imports), key=_direct_import_sort_key
        )
        expected_resolved_imports = sorted(
            [
                self.DIRECT_IMPORTS[0],
                self.DIRECT_IMPORTS[1],
                self.DIRECT_IMPORTS[3],
            ],
            key=_direct_import_sort_key,
        )
        expected_unresolved_imports = [
            ImportExpression(importer="mypackage.green", imported="mypackage.black.*")
        ]

        assert popped_direct_imports == expected_resolved_imports
        assert popped_unresolved_imports == expected_unresolved_imports
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

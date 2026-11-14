from __future__ import annotations

from textwrap import dedent

import pytest
from grimp import ImportGraph

from importlinter.application.contract_utils import MissingImport
from importlinter.application.output import console
from importlinter.contracts.private_modules import PrivateModulesContract, _is_private_module
from importlinter.domain.contract import ContractCheck


def _build_contract(**contract_options) -> PrivateModulesContract:
    return PrivateModulesContract(
        name="Private modules",
        session_options={"root_packages": ["mypackage"]},
        contract_options=contract_options,
    )


def _build_graph(*imports: tuple[str, str]) -> ImportGraph:
    graph = ImportGraph()
    for module in (
        "mypackage",
        "mypackage.foo",
        "mypackage.foo._private",
        "mypackage.foo._private.child",
        "mypackage.foo._private.child.grandchild",
        "mypackage.foo.sibling",
        "mypackage.foo.sibling.child",
        "mypackage.foo.sibling.child.grandchild",
        "mypackage.foo.public",
        "mypackage.foobar",
        "mypackage.other",
        "mypackage.other.child",
    ):
        graph.add_module(module)
    for importer, imported in imports:
        graph.add_import(importer=importer, imported=imported)
    return graph


class TestIsPrivateModule:
    @pytest.mark.parametrize(
        "module, expected",
        [
            ("mypackage.foo._bar", True),
            ("mypackage._bar", True),
            ("mypackage.foo.bar", False),
            ("mypackage._foo.bar", False),  # Only the last component counts.
            ("mypackage.foo.bar_", False),
            ("mypackage.foo.__main__", False),
            ("mypackage.foo.__version__", False),
            ("mypackage.foo.__bar", True),  # Only dunder names are exempt.
            ("_mypackage", False),  # Top level modules have no parent to be private to.
        ],
    )
    def test_is_private_module(self, module, expected):
        assert _is_private_module(module) is expected


class TestPrivateModulesContractCheck:
    @pytest.mark.parametrize(
        "importer",
        [
            "mypackage.foo",  # Parent.
            "mypackage.foo.sibling",  # Sibling.
            "mypackage.foo.sibling.child",  # Child of sibling.
            "mypackage.foo.sibling.child.grandchild",  # Grandchild of sibling.
            "mypackage.foo._private.child",  # Child.
            "mypackage.foo._private.child.grandchild",  # Grandchild.
        ],
    )
    def test_legal_imports_of_private_module(self, importer):
        graph = _build_graph((importer, "mypackage.foo._private"))

        check = _build_contract().check(graph, verbose=False)

        assert check.kept

    @pytest.mark.parametrize(
        "importer",
        [
            "mypackage",  # Grandparent.
            "mypackage.other",  # Sibling of parent.
            "mypackage.other.child",  # Child of sibling of parent.
            "mypackage.foobar",  # Not a descendant of the parent, despite the shared name prefix.
        ],
    )
    def test_illegal_imports_of_private_module(self, importer):
        graph = _build_graph((importer, "mypackage.foo._private"))

        check = _build_contract().check(graph, verbose=False)

        assert not check.kept
        assert [
            (link["importer"], link["imported"]) for link in check.metadata["illegal_imports"]
        ] == [(importer, "mypackage.foo._private")]

    @pytest.mark.parametrize(
        "imported",
        ["mypackage.foo._private.child", "mypackage.foo._private.child.grandchild"],
    )
    def test_descendants_of_private_module_are_private_too(self, imported):
        graph = _build_graph(("mypackage.other", imported))

        check = _build_contract().check(graph, verbose=False)

        assert not check.kept

    def test_descendants_of_private_module_can_be_imported_from_parent(self):
        graph = _build_graph(
            ("mypackage.foo.sibling", "mypackage.foo._private.child.grandchild"),
        )

        check = _build_contract().check(graph, verbose=False)

        assert check.kept

    def test_nested_private_module_is_private_to_its_own_parent(self):
        graph = ImportGraph()
        graph.add_import(importer="mypackage.foo.other", imported="mypackage.foo._one._two")
        graph.add_import(importer="mypackage.foo._one.sibling", imported="mypackage.foo._one._two")

        check = _build_contract().check(graph, verbose=False)

        assert not check.kept
        assert [link["importer"] for link in check.metadata["illegal_imports"]] == [
            "mypackage.foo.other"
        ]

    def test_import_is_only_reported_once_when_several_private_modules_are_involved(self):
        graph = ImportGraph()
        graph.add_import(importer="mypackage.other", imported="mypackage.foo._one._two")

        check = _build_contract().check(graph, verbose=False)

        # The import is illegal for both mypackage.foo._one and mypackage.foo._one._two.
        assert len(check.metadata["illegal_imports"]) == 1

    def test_public_modules_are_unrestricted(self):
        graph = _build_graph(("mypackage.other", "mypackage.foo.public"))

        check = _build_contract().check(graph, verbose=False)

        assert check.kept

    def test_indirect_imports_are_not_considered(self):
        graph = _build_graph(
            ("mypackage.other", "mypackage.foo.public"),
            ("mypackage.foo.public", "mypackage.foo._private"),
        )

        check = _build_contract().check(graph, verbose=False)

        assert check.kept

    def test_reports_line_numbers(self):
        graph = _build_graph()
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.foo._private",
            line_number=3,
            line_contents="from mypackage.foo import _private",
        )
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.foo._private",
            line_number=9,
            line_contents="from mypackage.foo import _private",
        )

        check = _build_contract().check(graph, verbose=False)

        assert check.metadata["illegal_imports"] == [
            {
                "importer": "mypackage.other",
                "imported": "mypackage.foo._private",
                "line_numbers": (3, 9),
            }
        ]

    def test_packages_limits_which_private_modules_are_checked(self):
        graph = _build_graph(
            ("mypackage.other", "mypackage.foo._private"),
            ("mypackage.foo", "mypackage.other._hidden"),
        )
        contract = _build_contract(packages=["mypackage.other"])

        check = contract.check(graph, verbose=False)

        # Only the private module in mypackage.other is checked.
        assert [
            (link["importer"], link["imported"]) for link in check.metadata["illegal_imports"]
        ] == [("mypackage.foo", "mypackage.other._hidden")]

    def test_packages_includes_descendants(self):
        graph = _build_graph(("mypackage.foobar", "mypackage.foo._private.child"))
        contract = _build_contract(packages=["mypackage.foo"])

        check = contract.check(graph, verbose=False)

        assert not check.kept

    def test_packages_supports_wildcards(self):
        graph = _build_graph(("mypackage.other", "mypackage.foo._private"))
        contract = _build_contract(packages=["mypackage.*"])

        check = contract.check(graph, verbose=False)

        assert not check.kept

    def test_private_module_outside_packages_is_not_checked(self):
        graph = _build_graph(("mypackage.other", "mypackage.foo._private"))
        contract = _build_contract(packages=["mypackage.other"])

        check = contract.check(graph, verbose=False)

        assert check.kept

    def test_packages_that_do_not_exist_raises(self):
        graph = _build_graph()
        contract = _build_contract(packages=["mypackage.nonexistent"])

        with pytest.raises(ValueError, match="mypackage.nonexistent"):
            contract.check(graph, verbose=False)

    def test_ignore_imports(self):
        graph = _build_graph(
            ("mypackage.other", "mypackage.foo._private"),
            ("mypackage.foobar", "mypackage.foo._private.child"),
        )
        contract = _build_contract(
            ignore_imports=["mypackage.other -> mypackage.foo._private"],
        )

        check = contract.check(graph, verbose=False)

        assert not check.kept
        assert check.ignored_import_count == 1
        assert [link["importer"] for link in check.metadata["illegal_imports"]] == [
            "mypackage.foobar"
        ]

    def test_ignore_imports_with_wildcards(self):
        graph = _build_graph(
            ("mypackage.other.child", "mypackage.foo._private.child"),
            ("mypackage.other.child", "mypackage.foo._private.child.grandchild"),
        )
        contract = _build_contract(
            ignore_imports=["mypackage.other.** -> mypackage.foo._private.**"]
        )

        check = contract.check(graph, verbose=False)

        assert check.kept
        assert check.ignored_import_count == 2

    def test_unmatched_ignore_imports_error_by_default(self):
        graph = _build_graph()
        contract = _build_contract(ignore_imports=["mypackage.other -> mypackage.foo._private"])

        with pytest.raises(MissingImport):
            contract.check(graph, verbose=False)

    @pytest.mark.parametrize(
        "alerting, expected_warnings",
        [
            ("none", 0),
            ("warn", 1),
        ],
    )
    def test_unmatched_ignore_imports_alerting(self, alerting, expected_warnings):
        graph = _build_graph()
        contract = _build_contract(
            ignore_imports=["mypackage.other -> mypackage.foo._private"],
            unmatched_ignore_imports_alerting=alerting,
        )

        check = contract.check(graph, verbose=False)

        assert check.kept
        assert len(check.warnings) == expected_warnings


class TestPrivateModulesContractRender:
    def test_render_broken_contract(self):
        graph = _build_graph()
        graph.add_import(
            importer="mypackage.other",
            imported="mypackage.foo._private",
            line_number=3,
            line_contents="from mypackage.foo import _private",
        )
        graph.add_import(
            importer="mypackage.foobar",
            imported="mypackage.foo._private.child",
            line_number=1,
            line_contents="from mypackage.foo._private import child",
        )
        contract = _build_contract()
        check = contract.check(graph, verbose=False)

        with console.capture() as capture:
            contract.render_broken_contract(check)

        assert capture.get() == dedent(
            """\
            Private modules may only be imported from within their parent package:

            - mypackage.foobar -> mypackage.foo._private.child (l.1)

            - mypackage.other -> mypackage.foo._private (l.3)

            """
        )

    def test_render_broken_contract_guidance(self):
        contract = _build_contract(broken_contract_guidance="Use the public API instead.")
        check = ContractCheck(
            kept=False,
            metadata={
                "illegal_imports": [
                    {
                        "importer": "mypackage.other",
                        "imported": "mypackage.foo._private",
                        "line_numbers": (3,),
                    }
                ]
            },
        )

        with console.capture() as capture:
            contract.render_broken_contract(check)

        assert "Use the public API instead." in capture.get()

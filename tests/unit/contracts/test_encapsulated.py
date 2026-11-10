from textwrap import dedent

import pytest
from grimp import ImportGraph

from importlinter.application.contract_utils import AlertLevel
from importlinter.application.output import console
from importlinter.contracts.encapsulated import EncapsulatedContract


class TestEncapsulatedContract:
    @staticmethod
    def _build_default_graph() -> ImportGraph:
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.service",
            "mypackage.service.api",
            "mypackage.service.api.schemas",
            "mypackage.service.internal",
            "mypackage.service.internal.deep",
            "mypackage.adapters",
            "mypackage.adapters.service",
            "mypackage.adapters.service.client",
            "mypackage.adapters.other",
            "mypackage.outside",
            "mypackage.outside.sub",
        ):
            graph.add_module(module)
        graph.add_module("django", is_squashed=True)
        return graph

    @staticmethod
    def _build_contract(**contract_options) -> EncapsulatedContract:
        all_options = {
            "modules": ("mypackage.service",),
            "public_modules": ("mypackage.service.api",),
            **contract_options,
        }
        return EncapsulatedContract(
            name="Encapsulated contract",
            session_options={"root_packages": ["mypackage"]},
            # Passing None for an option omits it.
            contract_options={k: v for k, v in all_options.items() if v is not None},
        )

    @pytest.mark.parametrize(
        "importer,imported,contract_kept,description",
        [
            (
                "mypackage.service.internal",
                "mypackage.service.api",
                True,
                "Imports within the modules are allowed",
            ),
            (
                "mypackage.service.api",
                "mypackage.service.internal.deep",
                True,
                "Public modules can import private modules in the same unit",
            ),
            (
                "mypackage.outside",
                "mypackage.service.api",
                True,
                "Other modules can import a public module",
            ),
            (
                "mypackage.outside.sub",
                "mypackage.service.api.schemas",
                True,
                "Other modules can import descendants of a public module",
            ),
            (
                "mypackage.outside",
                "mypackage.adapters.other",
                True,
                "Unrelated imports are not affected",
            ),
            (
                "mypackage.service.internal",
                "django",
                True,
                "Imports of external packages are not affected",
            ),
            (
                "mypackage.outside",
                "mypackage.service.internal",
                False,
                "Other modules cannot import a private module",
            ),
            (
                "mypackage.outside",
                "mypackage.service.internal.deep",
                False,
                "Other modules cannot import a descendant of a private module",
            ),
            (
                "mypackage.outside",
                "mypackage.service",
                False,
                "Other modules cannot import the encapsulated module itself",
            ),
            (
                "mypackage.service.internal",
                "mypackage.outside",
                False,
                "Private modules cannot import other modules",
            ),
            (
                "mypackage.service.api",
                "mypackage.outside.sub",
                False,
                "Public modules cannot import other modules",
            ),
            (
                "mypackage.service.internal",
                "mypackage",
                False,
                "Modules cannot import their parent package",
            ),
        ],
    )
    def test_imports(self, importer, imported, contract_kept, description):
        graph = self._build_default_graph()
        graph.add_import(importer=importer, imported=imported)
        contract = self._build_contract()

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept == contract_kept, description

    def test_no_imports(self):
        contract_check = self._build_contract().check(self._build_default_graph(), verbose=False)

        assert contract_check.kept

    def test_without_public_modules_nothing_can_be_imported(self):
        graph = self._build_default_graph()
        graph.add_import(importer="mypackage.outside", imported="mypackage.service.api")
        contract = EncapsulatedContract(
            name="Encapsulated contract",
            session_options={"root_packages": ["mypackage"]},
            contract_options={"modules": ("mypackage.service",)},
        )

        contract_check = contract.check(graph, verbose=False)

        assert not contract_check.kept

    def test_modules_in_different_locations_form_one_unit(self):
        graph = self._build_default_graph()
        # Imports between the two locations are internal.
        graph.add_import(
            importer="mypackage.adapters.service.client", imported="mypackage.service.internal"
        )
        graph.add_import(
            importer="mypackage.service.internal", imported="mypackage.adapters.service"
        )
        # But the second location is also protected from other modules.
        graph.add_import(
            importer="mypackage.outside", imported="mypackage.adapters.service.client"
        )
        contract = self._build_contract(
            modules=("mypackage.service", "mypackage.adapters.service")
        )

        contract_check = contract.check(graph, verbose=False)

        assert not contract_check.kept
        assert contract_check.metadata["outbound"] == []
        assert contract_check.metadata["inbound"] == [
            {
                "importer": "mypackage.outside",
                "imported": "mypackage.adapters.service.client",
                "line_numbers": (),
            }
        ]

    def test_wildcard_modules(self):
        graph = self._build_default_graph()
        graph.add_import(importer="mypackage.outside", imported="mypackage.adapters.other")
        contract = self._build_contract(modules=("mypackage.adapters.*",), public_modules=None)

        contract_check = contract.check(graph, verbose=False)

        assert not contract_check.kept

    @pytest.mark.parametrize(
        "importer,imported,allow_imports_to,contract_kept,description",
        [
            (
                "mypackage.service.internal",
                "mypackage.outside",
                ("mypackage.outside",),
                True,
                "The unit can import an allowed module",
            ),
            (
                "mypackage.service.api",
                "mypackage.outside.sub",
                ("mypackage.outside",),
                True,
                "The unit can import a descendant of an allowed module",
            ),
            (
                "mypackage.service.internal",
                "mypackage.adapters.other",
                ("mypackage.adapters.*",),
                True,
                "Allowed modules support wildcards",
            ),
            (
                "mypackage.service.internal",
                "mypackage.adapters.other",
                ("mypackage.outside",),
                False,
                "The unit still cannot import modules that aren't allowed",
            ),
            (
                "mypackage.outside",
                "mypackage.service.internal",
                ("mypackage.outside",),
                False,
                "Allowed modules still cannot import a private module",
            ),
            (
                "mypackage.outside",
                "mypackage.service.api",
                ("mypackage.outside",),
                True,
                "Allowed modules can still import a public module",
            ),
        ],
    )
    def test_allow_imports_to(
        self, importer, imported, allow_imports_to, contract_kept, description
    ):
        graph = self._build_default_graph()
        graph.add_import(importer=importer, imported=imported)
        contract = self._build_contract(allow_imports_to=allow_imports_to)

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept == contract_kept, description

    @pytest.mark.parametrize(
        "imported,contract_kept",
        [
            ("mypackage.adapters.other", True),
            ("mypackage.adapters", True),
            ("mypackage.outside", False),
        ],
    )
    def test_allow_imports_to_a_parent_package_of_the_unit(self, imported, contract_kept):
        graph = self._build_default_graph()
        graph.add_import(importer="mypackage.adapters.service.client", imported=imported)
        contract = self._build_contract(
            modules=("mypackage.adapters.service",),
            public_modules=None,
            allow_imports_to=("mypackage.adapters",),
        )

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept == contract_kept

    @pytest.mark.parametrize(
        "allow_imports_to",
        [("mypackage.service.internal",), ("mypackage.service",), ("mypackage.service.*",)],
    )
    def test_allow_imports_to_must_be_outside_modules(self, allow_imports_to):
        graph = self._build_default_graph()
        contract = self._build_contract(allow_imports_to=allow_imports_to)

        with pytest.raises(
            ValueError,
            match="Modules in allow_imports_to must be outside the encapsulated modules",
        ):
            contract.check(graph, verbose=False)

    def test_imports_outside_the_root_packages_are_not_affected(self):
        graph = self._build_default_graph()
        graph.add_module("otherpackage")
        graph.add_import(importer="mypackage.service.internal", imported="otherpackage")
        graph.add_import(importer="otherpackage", imported="mypackage.service.internal")
        contract = self._build_contract()

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept

    def test_ignore_imports(self):
        graph = self._build_default_graph()
        graph.add_import(importer="mypackage.outside", imported="mypackage.service.internal")
        graph.add_import(importer="mypackage.service.internal", imported="mypackage.outside.sub")
        contract = self._build_contract(
            ignore_imports=(
                "mypackage.outside -> mypackage.service.internal",
                "mypackage.service.internal -> mypackage.outside.sub",
            )
        )

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept
        assert contract_check.ignored_import_count == 2

    def test_ignore_imports_unmatched_alerting(self):
        graph = self._build_default_graph()
        contract = self._build_contract(
            ignore_imports=("mypackage.outside -> mypackage.service.internal",),
            unmatched_ignore_imports_alerting=AlertLevel.WARN.value,
        )

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept
        assert len(contract_check.warnings) == 1

    def test_metadata(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.outside.sub",
            imported="mypackage.service.internal",
            line_number=4,
            line_contents="import internal",
        )
        graph.add_import(
            importer="mypackage.service.internal.deep",
            imported="mypackage.outside",
            line_number=7,
            line_contents="import outside",
        )
        graph.add_import(
            importer="mypackage.service.internal.deep",
            imported="mypackage.outside",
            line_number=9,
            line_contents="import outside",
        )

        contract_check = self._build_contract().check(graph, verbose=False)

        assert contract_check.metadata == {
            "outbound": [
                {
                    "importer": "mypackage.service.internal.deep",
                    "imported": "mypackage.outside",
                    "line_numbers": (7, 9),
                }
            ],
            "inbound": [
                {
                    "importer": "mypackage.outside.sub",
                    "imported": "mypackage.service.internal",
                    "line_numbers": (4,),
                }
            ],
        }

    def test_public_modules_must_be_within_modules(self):
        graph = self._build_default_graph()
        contract = self._build_contract(public_modules=("mypackage.outside",))

        with pytest.raises(
            ValueError,
            match=(
                "Public modules must be within the encapsulated modules, "
                "but these are not: mypackage.outside."
            ),
        ):
            contract.check(graph, verbose=False)

    @pytest.mark.parametrize("option", ["modules", "public_modules", "allow_imports_to"])
    def test_modules_must_exist(self, option):
        graph = self._build_default_graph()
        contract = self._build_contract(**{option: ("mypackage.service.missing",)})

        with pytest.raises(ValueError, match="Module 'mypackage.service.missing' does not exist."):
            contract.check(graph, verbose=False)

    def test_render_broken_contract(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.outside.sub",
            imported="mypackage.service.internal",
            line_number=4,
            line_contents="import internal",
        )
        graph.add_import(
            importer="mypackage.service.internal.deep",
            imported="mypackage.outside",
            line_number=7,
            line_contents="import outside",
        )
        contract = self._build_contract(
            broken_contract_guidance="Use mypackage.service.api instead.\nMore info: http://docs"
        )
        contract_check = contract.check(graph, verbose=False)

        with console.capture() as capture:
            contract.render_broken_contract(contract_check)

        assert capture.get() == dedent(
            """\
            Imports out of the encapsulated modules are not allowed:

            - mypackage.service.internal.deep -> mypackage.outside (l.7)


            Imports into the encapsulated modules are only allowed via the public modules:

            - mypackage.outside.sub -> mypackage.service.internal (l.4)


            Use mypackage.service.api instead.
            More info: http://docs

            """
        )

    def test_render_broken_contract_without_public_modules(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.outside",
            imported="mypackage.service.api",
            line_number=2,
            line_contents="import api",
        )
        contract = self._build_contract(public_modules=None)
        contract_check = contract.check(graph, verbose=False)

        with console.capture() as capture:
            contract.render_broken_contract(contract_check)

        assert capture.get() == dedent(
            """\
            Imports into the encapsulated modules are not allowed:

            - mypackage.outside -> mypackage.service.api (l.2)


            """
        )

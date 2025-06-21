import pytest
from importlinter.contracts.protected import ProtectedContract
from importlinter.application.app_config import settings
from tests.adapters.printing import FakePrinter
from grimp.adaptors.graph import ImportGraph


class TestAllowListContract:
    @staticmethod
    def _build_default_graph() -> ImportGraph:
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.bar",
            "mypackage.bar.allowed",
            "mypackage.bar.allowed.three.blue",
            "mypackage.bar.allowed.one",
            "mypackage.bar.allowed.two",
            "mypackage.bar.other_package",
            "mypackage.bar.other_package.one",
            "mypackage.bar.other_package.two",
            "mypackage.foo.protected",
            "mypackage.foo.protected.models",
            "mypackage.foo.protected.other_models",
            "mypackage.foo.sibling",
            "mypackage.foo.sibling.models",
        ):
            graph.add_module(module)
        return graph

    @pytest.mark.parametrize(
        "import_details,contract_kept,description",
        [
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Allowed module can import protected",
            ),
            (
                {
                    "importer": "mypackage.foo.protected.other_models",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Modules in protected package can import each others",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.sibling.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Unrelated imports are still valid",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Allowed module can import children of protected",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Other packages are not allowed to import protected",
            ),
            (
                {
                    "importer": "mypackage.foo.sibling",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Siblings modules are not allowed to import protected",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed.three.blue",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Descendants of allowed module are not allowed to import protected",
            ),
        ],
    )
    def test_detects_illegal_imports_correctly_without_as_package(
        self, import_details, contract_kept, description
    ):
        # Tested contract says that the module mypackage.foo.protected.models can be imported
        # only from mypackage.foo.protected children and mypackage.bar.allowed children

        graph = self._build_default_graph()
        graph.add_import(**import_details)

        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": ("mypackage.foo.protected"),
                "allowed_importers": ("mypackage.bar.allowed"),
                "as_packages": "False",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    @pytest.mark.parametrize(
        "import_details,contract_kept,description",
        [
            (
                {
                    "importer": "mypackage.foo.protected.other_models",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Modules inside protected package can import each others",
            ),
            (
                {
                    "importer": "mypackage.foo.sibling.models",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Modules inside siblings of protected package are not allowed to import it",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Other modules are not allowed to protected ones",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.sibling.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Unrelated modules are still allowed to import each others",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Allowed package can import protected one at root level",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed.three.blue",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Deeper allowed modules are allowed to import protected ones",
            ),
        ],
    )
    def test_detects_illegal_imports_correctly_with_as_package(
        self, import_details, contract_kept, description
    ):
        # Tested contracts says the package mypackage.foo.protected can only be imported
        # from mypackage.bar.allowed
        graph = self._build_default_graph()
        graph.add_import(**import_details)

        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": ("mypackage.foo.protected"),
                "allowed_importers": ("mypackage.bar.allowed"),
                "as_packages": "True",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    @pytest.mark.parametrize(
        "import_details,contract_kept,description",
        [
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "mypackage.foo.protected",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Allowed module root can import protected root",
            ),
            (
                {
                    "importer": "mypackage.foo.protected.other_models",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Modules in protected expression can import each others",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.sibling.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Unrelated imports are still valid",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Allowed module expression root cannot import protected modules",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Other modules are not allowed to import protected",
            ),
            (
                {
                    "importer": "mypackage.foo.sibling",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Siblings of root are not allowed to import protected modules",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed.three.blue",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Descendants of allowed module are not allowed to import protected one",
            ),
        ],
    )
    def test_detects_illegal_imports_if_target_uses_wildcards_but_not_as_packages(
        self, import_details, contract_kept, description
    ):
        graph = self._build_default_graph()
        graph.add_import(**import_details)

        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": ("mypackage.foo.protected.*"),
                "allowed_importers": ("mypackage.bar.allowed.*"),
                "as_packages": "False",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    def test_render_broken_contract(self):
        settings.configure(PRINTER=FakePrinter())
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.bar.other_package.one",
            imported="mypackage.foo.protected.models",
            line_number=7,
            line_contents="print",
        )
        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": ("mypackage.foo.protected.models"),
                "allowed_importers": (
                    "mypackage.foo.protected",
                    "mypackage.bar.allowed",
                ),
                "as_packages": "true",
            },
        )
        contract_check = contract.check(graph=graph, verbose=False)
        contract.render_broken_contract(contract_check)
        assert (
            settings.PRINTER._buffer
            == """Following imports do not respect the protected policy:
mypackage.bar.other_package.one -> mypackage.foo.protected.models (l.7)

"""
        )

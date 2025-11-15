import pytest
from textwrap import dedent
from importlinter.application.output import console
from importlinter.contracts.protected import ProtectedContract
from grimp import ImportGraph


class TestProtectedContract:
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
            "mypackage.foo.protected.models.one",
            "mypackage.foo.protected.models.two",
            "mypackage.foo.protected.other_models",
            "mypackage.other_protected",
            "mypackage.other_protected.blue",
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
                "Modules inside protected package can import each other",
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
                "Modules not mentioned in the contract are not allowed to import protected ones",
            ),
            (
                {
                    "importer": "mypackage.other_protected.blue",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Other protected modules are not allowed to import protected ones",
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
                "protected_modules": [
                    "mypackage.foo.protected",
                    "mypackage.other_protected",
                ],
                "allowed_importers": ["mypackage.bar.allowed"],
                "as_packages": "True",
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)
        assert contract_check.kept == contract_kept, description

    def test_can_add_protected_modules_to_allowed_importers(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.other_protected.blue",
            imported="mypackage.foo.protected.models",
        )
        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": [
                    "mypackage.foo.protected",
                    "mypackage.other_protected",
                ],
                "allowed_importers": ["mypackage.other_protected"],
            },
        )

        contract_check = contract.check(graph=graph, verbose=False)

        assert contract_check.kept is True

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
                    "importer": "mypackage.foo.protected.models.one",
                    "imported": "mypackage.foo.protected.models.two",
                    "line_number": 3,
                    "line_contents": "print",
                },
                True,
                "Modules in same protected top-level module can import each others",
            ),
            (
                {
                    "importer": "mypackage.foo.protected.other_models",
                    "imported": "mypackage.foo.protected.models",
                    "line_number": 3,
                    "line_contents": "print",
                },
                False,
                "Modules in different protected top-level module cannot import each others",
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

    def test_handle_duplicated_illegal_imports(self):
        graph = self._build_default_graph()
        graph.add_import(
            importer="mypackage.bar.other_package.one",
            imported="mypackage.foo.protected.models",
            line_number=6,
            line_contents="import models",
        )
        graph.add_import(
            importer="mypackage.bar.other_package.one",
            imported="mypackage.foo.protected.models",
            line_number=27,
            line_contents="import models",
        )

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
        assert not contract_check.kept

    @pytest.mark.parametrize(
        "import_details,as_packages,contract_kept,description",
        [
            (
                {
                    "importer": "mypackage.bar.allowed",
                    "imported": "django",
                },
                "False",
                True,
                "Allowed module can import external protected module",
            ),
            (
                {
                    "importer": "mypackage.bar.allowed.one",
                    "imported": "django.core",
                },
                "True",
                True,
                "Allowed package can import external protected package",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package",
                    "imported": "django",
                },
                "False",
                False,
                "Non-allowed module cannot import external protected module",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package",
                    "imported": "mypackage.foo.sibling",
                },
                "False",
                True,
                "Unrelated imports are not affected without as_package",
            ),
            (
                {
                    "importer": "mypackage.bar.other_package.one",
                    "imported": "mypackage.foo.sibling",
                },
                "True",
                True,
                "Unrelated imports are not affected with as_package",
            ),
        ],
    )
    def test_protect_external_package(
        self, import_details, as_packages, contract_kept, description
    ):
        graph = self._build_default_graph()
        graph.add_module("django", is_squashed=True)
        graph.add_import(**import_details)
        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": ("django",),
                "allowed_importers": ("mypackage.bar.allowed",),
                "as_packages": as_packages,
            },
        )

        contract_check = contract.check(graph, verbose=False)

        assert contract_check.kept == contract_kept, description

    def test_render_broken_contract_simple_with_package(self):
        graph = self._build_default_graph()

        graph.add_import(
            importer="mypackage.foo.sibling",
            imported="mypackage.foo.protected.models",
            line_number=6,
            line_contents="import models",
        )

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

        with console.capture() as capture:
            contract.render_broken_contract(contract_check)

        assert not contract_check.kept
        assert capture.get() == dedent(
            """Illegal imports of protected package mypackage.foo.protected:

- mypackage.foo.sibling -> mypackage.foo.protected.models (l.6)


        """
        )

    def test_render_broken_contract_full_with_package(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.green",
            "mypackage.green.one",
            "mypackage.green.two",
            "mypackage.green.three",
            "mypackage.green.four",
            "mypackage.green.five",
            "mypackage.blue",
            "mypackage.blue.models",
            "mypackage.blue.models.alpha",
            "mypackage.yellow",
            "mypackage.yellow.one",
            "mypackage.orange",
            "mypackage.orange.data",
            "mypackage.brown",
            "mypackage.brown.alpha",
        ):
            graph.add_module(module)

        graph.add_import(
            importer="mypackage.green.one",
            imported="mypackage.blue.models",
            line_number=7,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.green.three",
            imported="mypackage.blue.models",
            line_number=12,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.green.three",
            imported="mypackage.blue.models",
            line_number=34,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.green.five",
            imported="mypackage.blue.models.alpha",
            line_number=4,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.yellow.one",
            imported="mypackage.orange.models",
            line_number=16,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.yellow.one",
            imported="mypackage.orange.data",
            line_number=17,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.yellow.one",
            imported="mypackage.brown",
            line_number=18,
            line_contents="print",
        )

        graph.add_import(
            importer="mypackage.yellow.one",
            imported="mypackage.brown.alpha",
            line_number=19,
            line_contents="print",
        )

        contract = ProtectedContract(
            name="Protected contract",
            session_options={
                "root_packages": ["mypackage"],
            },
            contract_options={
                "protected_modules": (
                    "mypackage.**.models",
                    "mypackage.**.data",
                    "mypackage.brown",
                ),
                "allowed_importers": ("mypackage.colors.*",),
                "as_packages": "true",
            },
        )
        contract_check = contract.check(graph=graph, verbose=False)

        with console.capture() as capture:
            contract.render_broken_contract(contract_check)

        assert capture.get() == dedent(
            """Illegal imports of protected package mypackage.blue.models
(via mypackage.**.models expression):

- mypackage.green.one -> mypackage.blue.models (l.7)

- mypackage.green.three -> mypackage.blue.models (l.12, 34)

- mypackage.green.five -> mypackage.blue.models.alpha (l.4)

Illegal imports of protected package mypackage.orange.models
(via mypackage.**.models expression):

- mypackage.yellow.one -> mypackage.orange.models (l.16)

Illegal imports of protected package mypackage.orange.data
(via mypackage.**.data expression):

- mypackage.yellow.one -> mypackage.orange.data (l.17)

Illegal imports of protected package mypackage.brown:

- mypackage.yellow.one -> mypackage.brown (l.18)

- mypackage.yellow.one -> mypackage.brown.alpha (l.19)


        """
        )

from unittest.mock import MagicMock, call, patch
from grimp.adaptors.graph import ImportGraph
from importlinter.contracts.acyclic import AcyclicContract, Cycle, _get_package_dependency
from importlinter.contracts.acyclic import _longest_common_package
from importlinter.domain.contract import ContractCheck


_ROOT_PACKAGE = "root"


def _build_contract(
    consider_package_dependencies: bool = True, max_cycle_families: int | None = None
) -> AcyclicContract:
    contract_options = {
        "packages": [_ROOT_PACKAGE],
        "consider_package_dependencies": str(consider_package_dependencies),
    }

    if max_cycle_families is not None:
        contract_options["max_cycle_families"] = str(max_cycle_families)

    return AcyclicContract(name="test", session_options={}, contract_options=contract_options)


class TestAcyclicContractCheck:
    def _get_test_graph(self) -> ImportGraph:
        """
        Return an import graph with two cycle families between packages.
        """
        graph = ImportGraph()
        graph.add_module(_ROOT_PACKAGE)

        for module in (
            f"{_ROOT_PACKAGE}.1_a",
            f"{_ROOT_PACKAGE}.1_a.2_a",
            f"{_ROOT_PACKAGE}.1_a.2_b",
            f"{_ROOT_PACKAGE}.1_b",
            f"{_ROOT_PACKAGE}.1_b.2_a",
            f"{_ROOT_PACKAGE}.1_b.2_b",
        ):
            graph.add_module(module)

        graph.add_import(
            importer=f"{_ROOT_PACKAGE}.1_a.2_a",
            imported=f"{_ROOT_PACKAGE}.1_b.2_b",
            line_number=1,
            line_contents="-",
        )
        graph.add_import(
            importer=f"{_ROOT_PACKAGE}.1_b.2_a",
            imported=f"{_ROOT_PACKAGE}.1_a.2_b",
            line_number=1,
            line_contents="-",
        )
        return graph

    def test_dag_indeed(self) -> None:
        # Given
        graph = ImportGraph()
        graph.add_module(_ROOT_PACKAGE)

        for module in (
            f"{_ROOT_PACKAGE}.1_a",
            f"{_ROOT_PACKAGE}.1_a.2_a",
            f"{_ROOT_PACKAGE}.1_a.2_b",
            f"{_ROOT_PACKAGE}.1_b",
            f"{_ROOT_PACKAGE}.1_b.2_a",
            f"{_ROOT_PACKAGE}.1_b.2_b",
            f"{_ROOT_PACKAGE}.1_c",
            f"{_ROOT_PACKAGE}.1_c.2_a",
            f"{_ROOT_PACKAGE}.1_c.2_b",
        ):
            graph.add_module(module)

        graph.add_import(importer=f"{_ROOT_PACKAGE}.1_a.2_a", imported=f"{_ROOT_PACKAGE}.1_b.2_b")
        graph.add_import(importer=f"{_ROOT_PACKAGE}.1_a.2_a", imported=f"{_ROOT_PACKAGE}.1_a.2_b")
        graph.add_import(importer=f"{_ROOT_PACKAGE}.1_a.2_b", imported=f"{_ROOT_PACKAGE}.1_c.2_a")
        graph.add_import(importer=f"{_ROOT_PACKAGE}.1_b.2_a", imported=f"{_ROOT_PACKAGE}.1_c.2_b")
        contract = _build_contract()
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert contract_check.kept

    def test_not_dag_structure(self) -> None:
        # Given
        graph = self._get_test_graph()
        contract = _build_contract()
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert not contract_check.kept

    def test_do_not_consider_package_dependencies(self) -> None:
        # Given
        graph = self._get_test_graph()
        contract = _build_contract(consider_package_dependencies=False)
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert contract_check.kept

    def test_max_cycle_families(self) -> None:
        # Given
        graph = self._get_test_graph()
        contract = _build_contract(max_cycle_families=1)
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        cycles = AcyclicContract._get_cycles_from_metadata(contract_check)
        assert len(cycles) == 1


class TestAcyclicContractRenderBrokenContract:
    @patch("importlinter.contracts.acyclic.output.print_error")
    def test_no_cycles(self, print_error_mock: MagicMock) -> None:
        # Given
        contract = _build_contract()
        contract_check = ContractCheck(kept=True)
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_not_called()

    @patch("importlinter.contracts.acyclic.output.print_error")
    def test_cycle_exists(self, print_error_mock: MagicMock) -> None:
        # Given
        contract = _build_contract()
        contract_check = ContractCheck(kept=True, metadata={})
        cycles = [
            Cycle(members=("1_a.2_a", "1_b.2_b", "1_a.2_b", "1_c.2_a"), package_lvl_cycle=True)
        ]
        AcyclicContract._set_cycles_in_metadata(check=contract_check, cycles=cycles)
        import_graph_mock = MagicMock()
        import_graph_mock.get_import_details = MagicMock(return_value=[{"line_number": 1}])
        AcyclicContract._set_graph_in_metadata(
            check=contract_check, import_graph=import_graph_mock
        )
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_has_calls(
            [
                call(text="\nPackage __root__ contains a (package) dependency cycle:"),
                call(text="\n  1. 1_a.2_a depends on 1_b.2_b:\n"),
                call(text="      - 1_a.2_a -> 1_b.2_b (l. 1)"),
                call(text="\n  2. 1_b.2_b depends on 1_a.2_b:\n"),
                call(text="      - 1_b.2_b -> 1_a.2_b (l. 1)"),
                call(text="\n  3. 1_a.2_b depends on 1_c.2_a:\n"),
                call(text="      - 1_a.2_b -> 1_c.2_a (l. 1)"),
                call(text="\n"),
            ]
        )


class TestLongestCommonPackage:
    def test_some_packages_and_root_in_cycle(self) -> None:
        # Given
        modules = (
            "django.core.paginator",
            "django.utils.translation",
            "django.utils.autoreload",
            "django",
            "django.core.paginator",
        )
        # When
        longest_common_package = _longest_common_package(modules=modules)
        # Then
        assert "django" == longest_common_package

    def test_short_cycle(self) -> None:
        # Given
        modules = ("django", "django.conf", "django")
        # When
        longest_common_package = _longest_common_package(modules=modules)
        # Then
        assert "django" == longest_common_package

    def test_no_common_package(self) -> None:
        # Given
        modules = (
            "a.b.c",
            "x.y.z",
            "m.n.o",
        )
        # When
        longest_common_package = _longest_common_package(modules=modules)
        # Then
        assert longest_common_package is None


class TestGetPackageDependency:
    def test_common_package_exist(self) -> None:
        # Given
        origin_dependency = ("a.b.c.x", "a.b.d.z")
        # When
        package_dependency = _get_package_dependency(
            importer=origin_dependency[0], imported=origin_dependency[1]
        )
        # Then
        assert ("a.b.c", "a.b.d") == package_dependency

    def test_no_common_package(self) -> None:
        # Given
        origin_dependency = ("a.b.c", "x.y.z")
        # When
        package_dependency = _get_package_dependency(
            importer=origin_dependency[0], imported=origin_dependency[1]
        )
        # Then
        assert ("a", "x") == package_dependency

from unittest.mock import MagicMock, call, patch
from grimp.adaptors.graph import ImportGraph
from importlinter.contracts.acyclic import AcyclicContract, Cycle
from importlinter.contracts.acyclic import _longest_common_package, _get_package_dependency
from importlinter.domain.contract import ContractCheck


def _build_contract(
    consider_package_dependencies: bool = True, max_cycle_families: int | None = None
) -> AcyclicContract:
    contract_options = {"consider_package_dependencies": str(consider_package_dependencies)}

    if max_cycle_families is not None:
        contract_options["max_cycle_families"] = str(max_cycle_families)

    return AcyclicContract(name="test", session_options={}, contract_options=contract_options)


class TestAcyclicContractCheck:
    def _get_test_graph(self) -> ImportGraph:
        """
        Return an import graph with two cycle families between packages.
        """
        graph = ImportGraph()

        for module in (
            "root.1_a",
            "root.1_a.2_a",
            "root.1_a.2_b",
            "root.1_b",
            "root.1_b.2_a",
            "root.1_b.2_b",
        ):
            graph.add_module(module)

        graph.add_import(importer="root.1_a.2_a", imported="root.1_b.2_b")
        graph.add_import(importer="root.1_b.2_a", imported="root.1_a.2_b")
        return graph

    def test_dag_indeed(self) -> None:
        # Given
        graph = ImportGraph()

        for module in (
            "root.1_a",
            "root.1_a.2_a",
            "root.1_a.2_b",
            "root.1_b",
            "root.1_b.2_a",
            "root.1_b.2_b",
            "root.1_c",
            "root.1_c.2_a",
            "root.1_c.2_b",
        ):
            graph.add_module(module)

        graph.add_import(importer="root.1_a.2_a", imported="root.1_b.2_b")
        graph.add_import(importer="root.1_a.2_a", imported="root.1_a.2_b")
        graph.add_import(importer="root.1_a.2_b", imported="root.1_c.2_a")
        graph.add_import(importer="root.1_b.2_a", imported="root.1_c.2_b")
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
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_has_calls(
            [
                call(text=">>>> Cycles family for parent module '1_a'"),
                call(text="\nSiblings:\n(\n  1_a\n  1_b\n)"),
                call(text="\nNumber of cycles: 1\n"),
                call(
                    text="Cycle 1:\n\n(\n -> 1_a.2_a\n -> 1_b.2_b\n -> 1_a.2_b\n -> 1_c.2_a\n)\n"
                ),
                call(text="<<<< Cycles family for parent module '1_a'\n"),
                call(text="Number of cycle families found for a contract 'test': 1\n"),
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

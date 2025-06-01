from unittest.mock import MagicMock, call, patch
from grimp.adaptors.graph import ImportGraph
from importlinter.contracts.acyclic import AcyclicContract, Cycle, CyclesFamily, CyclesFamilyKey
from importlinter.domain.contract import ContractCheck


def _build_contract(consider_package_dependencies: bool = True) -> AcyclicContract:
    return AcyclicContract(name="test", session_options={}, contract_options={
        "consider_package_dependencies": str(consider_package_dependencies)
    })


class TestAcyclicContractCheck:
    """
    Naming convention for modules:

    <level_in_the_directory_tree>_<hierarchy_lvl_in_the_package>

    """

    def test_dag_indeed(self) -> None:
        # Given
        graph = ImportGraph()

        for module in (
            "1_a",
            "1_a.2_a",
            "1_a.2_b",
            "1_b",
            "1_b.2_a",
            "1_b.2_b",
            "1_c",
            "1_c.2_a",
            "1_c.2_b",
        ):
            graph.add_module(module)

        graph.add_import(importer="1_a.2_a", imported="1_b.2_b")
        graph.add_import(importer="1_a.2_a", imported="1_a.2_b")
        graph.add_import(importer="1_a.2_b", imported="1_c.2_a")
        graph.add_import(importer="1_b.2_a", imported="1_c.2_b")
        contract = _build_contract()
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert contract_check.kept

    def test_not_dag_structure(self) -> None:
        # Given
        graph = ImportGraph()

        for module in ("1_a", "1_a.2_a", "1_a.2_b", "1_b", "1_b.2_a", "1_b.2_b"):
            graph.add_module(module)

        graph.add_import(importer="1_a.2_a", imported="1_b.2_b")
        graph.add_import(importer="1_b.2_a", imported="1_a.2_b")
        contract = _build_contract()
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert not contract_check.kept

    def test_do_not_consider_package_dependencies(self) -> None:
        # Given
        graph = ImportGraph()

        for module in ("1_a", "1_a.2_a", "1_a.2_b", "1_b", "1_b.2_a", "1_b.2_b"):
            graph.add_module(module)

        graph.add_import(importer="1_a.2_a", imported="1_b.2_b")
        graph.add_import(importer="1_b.2_a", imported="1_a.2_b")
        contract = _build_contract(consider_package_dependencies=False)
        # When
        contract_check = contract.check(graph=graph, verbose=False)
        # Then
        assert contract_check.kept


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
        contract_check = ContractCheck(
            kept=True, metadata={}
        )
        cycle_families = [
            CyclesFamily(
                key=CyclesFamilyKey(parent="1_a", sibilings=("1_a", "1_b")),
                cycles=[Cycle(members=("1_a.2_a", "1_b.2_b", "1_a.2_b", "1_c.2_a"))]
            )
        ]
        AcyclicContract._set_cycles_in_metadata( # type: ignore , just mocking
            check=contract_check,
            cycle_families=cycle_families
        )
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_has_calls([
            call(text='Acyclic contract broken. Number of cycle families found: 1\n'),
            call(text=">>>> Cycle family for parent module '1_a'\n"),
            call(text='\nSibilings:\n(\n  1_a\n  1_b\n)\n'),
            call(text='\nNumber of cycles: 1\n'),
            call(text='Cycle 1:\n\n(\n -> 1_a.2_a\n -> 1_b.2_b\n -> 1_a.2_b\n -> 1_c.2_a\n)\n'),
            call(text="<<<< Cycle family for parent module '1_a'\n")
        ])

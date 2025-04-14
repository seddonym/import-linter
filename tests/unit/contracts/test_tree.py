from unittest.mock import MagicMock, patch
from grimp.adaptors.graph import ImportGraph
from importlinter.contracts.tree import TreeContract
from importlinter.domain.contract import ContractCheck


def _build_contract() -> TreeContract:
    return TreeContract(name="test", session_options=dict(), contract_options=dict())


class TestTreeContractCheck:
    """
    Naming convention for modules:

    <level_in_the_directory_tree>_<hierarchy_lvl_in_the_package>

    """

    def test_tree_indeed(self) -> None:
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

    def test_not_a_tree(self) -> None:
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
        pass  # TODO


class TestTreeContractRenderBrokenContract:
    @patch("importlinter.contracts.tree.output.print_error")
    @patch("importlinter.contracts.tree.output.new_line")
    def test_no_cycles(self, new_line_mock: MagicMock, print_error_mock: MagicMock) -> None:
        # Given
        contract = _build_contract()
        contract_check = ContractCheck(kept=True)
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_not_called()
        new_line_mock.assert_not_called()

    @patch("importlinter.contracts.tree.output.print_error")
    @patch("importlinter.contracts.tree.output.new_line")
    def test_cycle_exists(self, new_line_mock: MagicMock, print_error_mock: MagicMock) -> None:
        # Given
        contract = _build_contract()
        contract_check = ContractCheck(
            kept=True, metadata={contract._CYCLES_METADATA_KEY: [["1_b", "1_a"]]}
        )
        # When
        contract.render_broken_contract(check=contract_check)
        # Then
        print_error_mock.assert_called_once_with(text="Cycle found: ['1_b', '1_a']")
        new_line_mock.assert_called_once_with()

import pytest
from grimp import ImportGraph

from importlinter.application import rendering
from importlinter.application.output import console
from tests.helpers.contracts import AlwaysFailsContract, AlwaysPassesContract


class TestRenderContractResultLine:
    """
    Covers the "(...)" suffix that follows a contract's KEPT/BROKEN result: the ignored
    imports count and the warnings count, combined into a single clause.
    """

    @pytest.mark.parametrize(
        "ignored_import_count, warning_messages, expected_line",
        [
            (0, [], "My contract KEPT"),
            (19, [], "My contract KEPT (19 ignored imports)"),
            (1, [], "My contract KEPT (1 ignored import)"),
            (0, ["A warning."], "My contract KEPT (1 warning)"),
            (0, ["One.", "Two."], "My contract KEPT (2 warnings)"),
            (19, ["A warning."], "My contract KEPT (19 ignored imports, 1 warning)"),
        ],
    )
    def test_kept_contract(self, ignored_import_count, warning_messages, expected_line):
        contract = AlwaysPassesContract(
            name="My contract",
            session_options={},
            contract_options={
                "ignored_import_count": ignored_import_count,
                "warnings": warning_messages,
            },
        )
        contract_check = contract.check(ImportGraph(), verbose=False)

        with console.capture() as capture:
            rendering.render_contract_result_line(contract, contract_check, duration=None)

        assert capture.get() == f"{expected_line}\n"

    def test_broken_contract_with_no_ignored_imports_or_warnings(self):
        contract = AlwaysFailsContract(name="My contract", session_options={}, contract_options={})
        contract_check = contract.check(ImportGraph(), verbose=False)

        with console.capture() as capture:
            rendering.render_contract_result_line(contract, contract_check, duration=None)

        assert capture.get() == "My contract BROKEN\n"


@pytest.mark.parametrize(
    "milliseconds, expected",
    [
        (0, "0.000s"),
        (1, "0.001s"),
        (532, "0.532s"),
        (999, "0.999s"),
        (1000, "1.0s"),
        (1234, "1.2s"),
        (9950, "9.9s"),
        (9999, "10.0s"),  # a bit ugly but not really worth fixing
        (10000, "10s"),
        (12400, "12s"),
    ],
)
def test_format_duration(milliseconds, expected):
    assert rendering.format_duration(milliseconds) == expected

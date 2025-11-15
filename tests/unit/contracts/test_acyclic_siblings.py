from importlinter.contracts.acyclic_siblings import AcyclicSiblingsContract
import string

from importlinter.domain.contract import InvalidContractOptions, ContractCheck
import grimp
import pytest
from textwrap import dedent
from importlinter.application.output import console

from tests.adapters.timing import FakeTimer
from importlinter.application.app_config import settings
from importlinter.contracts.acyclic_siblings import PackageSummary, Dependency


@pytest.fixture(scope="module", autouse=True)
def configure():
    settings.configure(TIMER=FakeTimer())


class TestAcyclicSiblingsContractCheck:
    @pytest.mark.parametrize(
        "ancestors, expected_message",
        (
            (["nonexistent"], "Module 'nonexistent' does not exist."),
            (["pkg", "nonexistent"], "Module 'nonexistent' does not exist."),
            # For multiple failures, we just report on the one earlier in the alphabet.
            (
                ["pkg", "pkg.nonexistent_b", "pkg.nonexistent_a"],
                "Module 'pkg.nonexistent_a' does not exist.",
            ),
            (["pkg.green.*"], "The expression 'pkg.green.*' did not match any modules."),
        ),
    )
    def test_no_such_ancestor(self, ancestors, expected_message):
        graph = grimp.ImportGraph()
        graph.add_module("pkg")
        graph.add_module("pkg.blue")
        contract = _build_contract(ancestors=ancestors)

        with pytest.raises(ValueError, match=expected_message):
            _check(contract, graph)

    def test_ancestor_with_no_children(self):
        graph = grimp.ImportGraph()
        graph.add_module("pkg")
        contract = _build_contract()

        check = _check(contract, graph)

        assert check.kept is True

    def test_root_ancestor_depth_zero_no_cycles(self):
        graph = _build_acyclic_graph()
        contract = _build_contract(depth="0")

        check = _check(contract, graph)

        assert check.kept is True

    @pytest.mark.parametrize(
        "ancestors, skip_descendants, expected_message",
        (
            (["pkg"], ["pkg"], "Cannot skip 'pkg' as it is also an ancestor."),
            (["pkg.foo"], ["pkg.foo"], "Cannot skip 'pkg.foo' as it is also an ancestor."),
            # This one's ok.
            (["pkg.*"], ["pkg.foo"], None),
            # Identical expressions aren't allowed.
            (
                ["pkg.*"],
                ["pkg.*"],
                "Cannot skip descendant 'pkg.*' as the same expression is in ancestors.",
            ),
            # Allow skipping of all ancestors (maybe a warning would be a good idea?)
            (["pkg.foo"], ["pkg.*"], None),
            (["pkg.*"], ["nonexistent"], "Module 'nonexistent' does not exist."),
        ),
    )
    def test_skip_descendants(self, ancestors, skip_descendants, expected_message):
        graph = _build_acyclic_graph()
        contract = _build_contract(ancestors=ancestors, skip_descendants=skip_descendants)

        if expected_message is None:
            _check(contract, graph)
        else:
            with pytest.raises(ValueError, match=expected_message):
                _check(contract, graph)

    CYCLE_BREAKERS_PKG = {("pkg.foo.blue", "pkg.bar.yellow")}
    SUMMARY_PKG = PackageSummary(
        package="pkg",
        dependencies=frozenset({Dependency("pkg.foo", "pkg.bar", 1)}),
    )
    CYCLE_BREAKERS_PKG_FOO = {
        ("pkg.foo.green.two.gamma", "pkg.foo.blue.one"),
        ("pkg.foo.green.two.gamma", "pkg.foo.blue"),
        ("pkg.foo.green.two.gamma.a", "pkg.foo.blue.one"),
    }
    SUMMARY_PKG_FOO = PackageSummary(
        package="pkg.foo",
        dependencies=frozenset({Dependency("pkg.foo.green", "pkg.foo.blue", 3)}),
    )
    CYCLE_BREAKERS_PKG_FOO_GREEN = {
        ("pkg.foo.green.four", "pkg.foo.green.two.gamma"),
        ("pkg.foo.green.four", "pkg.foo.green.three.delta"),
    }
    SUMMARY_PKG_FOO_GREEN = PackageSummary(
        package="pkg.foo.green",
        dependencies=frozenset(
            {
                Dependency("pkg.foo.green.four", "pkg.foo.green.two", 1),
                Dependency("pkg.foo.green.four", "pkg.foo.green.three", 1),
            }
        ),
    )
    CYCLE_BREAKERS_PKG_FOO_GREEN_TWO = {("pkg.foo.green.two.gamma", "pkg.foo.green.two.beta")}
    SUMMARY_PKG_FOO_GREEN_TWO = PackageSummary(
        package="pkg.foo.green.two",
        dependencies=frozenset(
            {Dependency("pkg.foo.green.two.gamma", "pkg.foo.green.two.beta", 1)}
        ),
    )
    CYCLE_BREAKERS_PKG_BAR_RED = {("pkg.bar.red.six", "pkg.bar.red.five")}
    SUMMARY_PKG_BAR_RED = PackageSummary(
        package="pkg.bar.red",
        dependencies=frozenset({Dependency("pkg.bar.red.six", "pkg.bar.red.five", 1)}),
    )

    @pytest.mark.parametrize(
        "ancestors, depth, skip_descendants, ignore_imports, expected",
        (
            (
                ["pkg"],
                "0",
                [],
                [],
                {
                    "cycle_breakers_by_package": {
                        "pkg": CYCLE_BREAKERS_PKG,
                    },
                    "summaries": {SUMMARY_PKG},
                },
            ),
            (
                ["pkg.foo", "pkg.foo.green.two"],
                "0",
                [],
                [],
                {
                    "cycle_breakers_by_package": {
                        "pkg.foo": CYCLE_BREAKERS_PKG_FOO,
                        "pkg.foo.green.two": CYCLE_BREAKERS_PKG_FOO_GREEN_TWO,
                    },
                    "summaries": {SUMMARY_PKG_FOO, SUMMARY_PKG_FOO_GREEN_TWO},
                },
            ),
            (
                ["pkg"],
                "1",
                [],
                [],
                {
                    "cycle_breakers_by_package": {
                        "pkg": CYCLE_BREAKERS_PKG,
                        "pkg.foo": CYCLE_BREAKERS_PKG_FOO,
                    },
                    "summaries": {SUMMARY_PKG, SUMMARY_PKG_FOO},
                },
            ),
            (
                ["pkg"],
                None,
                [],
                [],
                {
                    "cycle_breakers_by_package": {
                        "pkg": CYCLE_BREAKERS_PKG,
                        "pkg.foo": CYCLE_BREAKERS_PKG_FOO,
                        "pkg.foo.green": CYCLE_BREAKERS_PKG_FOO_GREEN,
                        "pkg.foo.green.two": CYCLE_BREAKERS_PKG_FOO_GREEN_TWO,
                        "pkg.bar.red": CYCLE_BREAKERS_PKG_BAR_RED,
                    },
                    "summaries": {
                        SUMMARY_PKG,
                        SUMMARY_PKG_FOO,
                        SUMMARY_PKG_FOO_GREEN,
                        SUMMARY_PKG_FOO_GREEN_TWO,
                        SUMMARY_PKG_BAR_RED,
                    },
                },
            ),
            (
                ["pkg"],
                None,
                [
                    "pkg.foo.green"  # Skipped descendant.
                ],
                [],
                {
                    "cycle_breakers_by_package": {
                        "pkg": CYCLE_BREAKERS_PKG,
                        "pkg.foo": CYCLE_BREAKERS_PKG_FOO,
                        "pkg.bar.red": CYCLE_BREAKERS_PKG_BAR_RED,
                    },
                    "summaries": {SUMMARY_PKG, SUMMARY_PKG_FOO, SUMMARY_PKG_BAR_RED},
                },
            ),
            (
                ["pkg"],
                None,
                [
                    "pkg.foo.green"  # Skipped descendant.
                ],
                ["pkg.bar.red.six -> pkg.bar.red.five"],  # Ignored import.
                {
                    "cycle_breakers_by_package": {
                        "pkg": CYCLE_BREAKERS_PKG,
                        "pkg.foo": CYCLE_BREAKERS_PKG_FOO,
                    },
                    "summaries": {SUMMARY_PKG, SUMMARY_PKG_FOO},
                },
            ),
        ),
    )
    def test_with_cycles(self, ancestors, depth, skip_descendants, ignore_imports, expected):
        graph = _build_acyclic_graph()
        contract = _build_contract(
            ancestors=ancestors,
            skip_descendants=skip_descendants,
            depth=depth,
            ignore_imports=ignore_imports,
        )
        # Add cycles.
        for importer, imported in (
            # bar depends on foo.
            ("pkg.bar.red", "pkg.foo.orange"),
            # green depends on blue - 3 ways. But these will still be selected
            # as blue depends on green in 5 ways.
            ("pkg.foo.green.two.gamma", "pkg.foo.blue.one"),
            ("pkg.foo.green.two.gamma", "pkg.foo.blue"),
            ("pkg.foo.green.two.gamma.a", "pkg.foo.blue.one"),
            # four depends on two, and on three. These will still be selected
            # as there are more in the 3-cycle in the other direction.
            ("pkg.foo.green.four", "pkg.foo.green.two.gamma"),
            ("pkg.foo.green.four", "pkg.foo.green.three.delta"),
            # gamma depends on beta.
            ("pkg.foo.green.two.gamma", "pkg.foo.green.two.beta"),
            # six depends on five.
            ("pkg.bar.red.six", "pkg.bar.red.five"),
        ):
            graph.add_import(importer=importer, imported=imported)
        check = _check(contract, graph)

        assert check.kept is False
        assert check.metadata == expected


class TestAcyclicSiblingsContractValidate:
    def test_depth_must_not_be_negative(self):
        with pytest.raises(InvalidContractOptions) as exc:
            _build_contract(depth="-1")
        assert exc.value.errors == {"depth": "Must be >= 0."}


def _build_acyclic_graph() -> grimp.ImportGraph:
    graph = grimp.ImportGraph()
    for module in (
        "pkg",
        "pkg.foo",
        "pkg.foo.blue",
        "pkg.foo.blue.one",
        "pkg.foo.green",
        "pkg.foo.green.two",
        "pkg.foo.green.two.beta",
        "pkg.foo.green.two.gamma",
        "pkg.foo.green.two.gamma.a",
        "pkg.foo.green.two.gamma.b",
        "pkg.foo.green.two.gamma.c",
        "pkg.foo.green.three",
        "pkg.foo.green.three.delta",
        "pkg.foo.green.three.epsilon",
        "pkg.foo.green.four",
        "pkg.foo.orange",
        "pkg.bar",
        "pkg.bar.yellow",
        "pkg.bar.red",
        "pkg.bar.red.five",
        "pkg.bar.red.six",
    ):
        graph.add_module(module)
    for importer, imported in (
        # foo depends on bar.
        ("pkg.foo.blue", "pkg.bar.yellow"),
        # blue depends on green in 5 ways. This will allow us to
        # add multiple imports (< 5) in the other direction and they'll still be
        # picked as cycle breakers.
        ("pkg.foo.blue", "pkg.foo.green.two.beta"),
        ("pkg.foo.blue.one", "pkg.foo.green.two.gamma"),
        ("pkg.foo.blue", "pkg.foo.green.two.gamma.a"),
        ("pkg.foo.blue.one", "pkg.foo.green.two.gamma.b"),
        ("pkg.foo.blue", "pkg.foo.green.two.gamma.c"),
        # two depends on three, depends on four.
        ("pkg.foo.green.two.beta", "pkg.foo.green.three.delta"),
        ("pkg.foo.green.two.beta", "pkg.foo.green.three.epsilon"),
        ("pkg.foo.green.three.delta", "pkg.foo.green.four"),
        ("pkg.foo.green.three.epsilon", "pkg.foo.green.four"),
        # beta depends on gamma.
        ("pkg.foo.green.two.beta", "pkg.foo.green.two.gamma"),
        # five depends on six.
        ("pkg.bar.red.five", "pkg.bar.red.six"),
    ):
        graph.add_import(importer=importer, imported=imported)

    return graph


def _build_contract(
    ancestors: list[str] | None = None,
    skip_descendants: list[str] | None = None,
    depth: str = "",
    ignore_imports: list[str] | None = None,
) -> AcyclicSiblingsContract:
    contract_options: dict[str, list[str] | str] = {"ancestors": ancestors or ["pkg"]}
    if skip_descendants:
        contract_options["skip_descendants"] = skip_descendants
    if depth:
        contract_options["depth"] = depth
    if ignore_imports:
        contract_options["ignore_imports"] = ignore_imports
    return AcyclicSiblingsContract(
        name="My contract",
        session_options={"root_packages": ["pkg"]},
        contract_options=contract_options,
    )


def _check(contract: AcyclicSiblingsContract, graph: grimp.ImportGraph) -> ContractCheck:
    return contract.check(graph, verbose=False)


class TestVerbosePrint:
    def test_verbose(self):
        timer = FakeTimer()
        timer.setup(tick_duration=10, increment=0)
        settings.configure(TIMER=timer)
        graph = _build_acyclic_graph()
        # Add cycles.
        for importer, imported in (
            # Green depends on blue.
            ("pkg.foo.green.two.gamma", "pkg.foo.blue.one"),
            ("pkg.foo.green.two.gamma", "pkg.foo.blue"),
            ("pkg.foo.green.two.gamma.a", "pkg.foo.blue.one"),
            # four depends on two.
            ("pkg.foo.green.four", "pkg.foo.green.two.gamma"),
        ):
            graph.add_import(importer=importer, imported=imported)
        contract = _build_contract()

        with console.capture() as capture:
            contract.check(graph=graph, verbose=True)

        assert capture.get() == dedent(
            """\
            Searching for cycles between children of pkg...
            No cycles found (10s).
            Searching for cycles between children of pkg.bar...
            No cycles found (10s).
            Searching for cycles between children of pkg.bar.red...
            No cycles found (10s).
            Searching for cycles between children of pkg.foo...
            Found 3 cycles in 10s.
            Searching for cycles between children of pkg.foo.green...
            Found 1 cycle in 10s.
            Searching for cycles between children of pkg.foo.green.three...
            No cycles found (10s).
            Searching for cycles between children of pkg.foo.green.two...
            No cycles found (10s).
            Searching for cycles between children of pkg.foo.green.two.gamma...
            No cycles found (10s).
            """
        )


class TestRenderBrokenContract:
    def test_render(self):
        contract = _build_contract()
        check = ContractCheck(
            kept=False,
            metadata={
                "summaries": {
                    PackageSummary(
                        package="pkg",
                        dependencies=frozenset(
                            {
                                Dependency(
                                    downstream="pkg.foo",
                                    upstream="pkg.bar",
                                    num_imports=10,
                                ),
                            }
                        ),
                    ),
                    PackageSummary(
                        package="pkg.foo.green",
                        dependencies=frozenset(
                            {
                                Dependency(
                                    downstream=f"pkg.foo.green.child_{char}",
                                    upstream=f"pkg.foo.green.child_{char}2",
                                    num_imports=3,
                                )
                                for char in string.ascii_lowercase[:12]
                            }
                        ),
                    ),
                    PackageSummary(
                        package="pkg.foo",
                        dependencies=frozenset(
                            {
                                Dependency(
                                    downstream="pkg.foo.green",
                                    upstream="pkg.foo.yellow",
                                    num_imports=1,
                                ),
                                Dependency(
                                    downstream="pkg.foo.blue",
                                    upstream="pkg.foo.green",
                                    num_imports=4,
                                ),
                            }
                        ),
                    ),
                },
            },
        )

        with console.capture() as capture:
            contract.render_broken_contract(check)

        assert capture.get() == dedent(
            """\
            No cycles are allowed in pkg.
            It could be made acyclic by removing 1 dependency:
            
            - .foo -> .bar (10 imports)
            
            No cycles are allowed in pkg.foo.
            It could be made acyclic by removing 2 dependencies:
            
            - .blue -> .green (4 imports)
            - .green -> .yellow (1 import)
                
            No cycles are allowed in pkg.foo.green.
            It could be made acyclic by removing 12 dependencies:
            
            - .child_a -> .child_a2 (3 imports)
            - .child_b -> .child_b2 (3 imports)
            - .child_c -> .child_c2 (3 imports)
            - .child_d -> .child_d2 (3 imports)
            - .child_e -> .child_e2 (3 imports)
            (and 7 more).
    
            """
        )

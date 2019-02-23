from .ports.reporting import Report
from .ports.printing import Printer


def render_report(report: Report, printer: Printer) -> None:
    printer.print("""
    =============
    Import Linter
    =============
    """)

    printer.print("""
    ---------
    Contracts
    ---------
    """)

    printer.print("""
    Analyzed 23 files, 44 dependencies.
    -----------------------------------

    Contract foo KEPT
    Contract bar KEPT

    Contracts: 2 kept, 0 broken.
    """)

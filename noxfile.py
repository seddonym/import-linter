import nox
import nox_uv

nox.options.default_venv_backend = "uv"

PYPROJECT = nox.project.load_toml("pyproject.toml")
PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)
EARLIEST_PYTHON = PYTHON_VERSIONS[0]


@nox_uv.session(
    python=PYTHON_VERSIONS,
    uv_groups=["dev"],
)
def test_with_ui_deps_installed(session: nox.Session) -> None:
    """
    Run tests that assume the `ui` extra is installed.

    (This is most of the tests.)
    """
    session.run("pytest", "-m", "not no_ui_deps_installed")


@nox_uv.session(
    python=PYTHON_VERSIONS,
    uv_groups=["dev-minimal"],
)
def test_without_ui_deps_installed(session: nox.Session) -> None:
    """
    Run the tests that are specifically for when the `ui` extra is not installed.
    """
    session.run("pytest", "-m", "no_ui_deps_installed")

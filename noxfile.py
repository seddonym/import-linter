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


@nox.session(python=[EARLIEST_PYTHON])
@nox.parametrize("with_ui", [True, False])
def test_earliest_dependencies(session: nox.Session, with_ui: bool) -> None:
    """
    Try to detect any compatibility issues with lower bounds of our dependencies.

    We run the tests on the earliest version of Python and use the lowest-direct resolution
    strategy to install the lowest direct dependencies listed in pyproject.toml.
    """
    session.install("uv")

    if with_ui:
        # Install ui extra.
        package = ".[ui]"
        group = "dev"
        # Run all tests except the ones that should only be run when the ui deps aren't installed.
        pytest_mark = "not no_ui_deps_installed"
    else:
        package = "."
        group = "dev-minimal"
        # Run the tests specifically for when the ui deps aren't installed.
        pytest_mark = "no_ui_deps_installed"

    # We can't use nox_uv for this one, nor `uv run`, as it will overwrite the project's uv.lock file.
    # Instead we use uv to install the lowest dependencies into the virtualenv provided by nox.
    session.run(
        "uv",
        "pip",
        "install",
        package,
        "--group",
        group,
        "--resolution=lowest-direct",
        env={"VIRTUAL_ENV": session.virtualenv.location},
    )

    session.run("pytest", "-m", pytest_mark)

# Install

Install `import-linter` using your favorite Python package manager. (You probably only want it as a dev dependency.)

=== "pip"
    ```console
    pip install import-linter
    ```

=== "uv"
    ```console
    uv add --dev import-linter
    ```

=== "poetry"
    ```console
    poetry add import-linter --group dev
    ```

## Dependencies of the Interactive UI {: #ui-dependencies }

[Import Linter's UI](../ui.md) requires some extra dependencies, not needed by the linter.
These are available in the `ui` [extra](https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras). To install:

=== "pip"
    ```console
    pip install "import-linter[ui]"
    ```

=== "uv"
    ```console
    uv add --dev "import-linter[ui]"
    ```

=== "poetry"
    ```console
    poetry add "import-linter[ui]" --group dev
    ```

# Configure

Before [running Import Linter](run.md), you need to supply configuration in one or more files.

## Configuration file location

If not specified over the command line, Import Linter will look in the current directory for one of the following files:

- `setup.cfg` (INI format)
- `.importlinter` (INI format)
- `pyproject.toml` (TOML format)

## Top level configuration

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage
    # Optional:
    include_external_packages = True
    exclude_type_checking_imports = True
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"
    # Optional:
    include_external_packages = true
    exclude_type_checking_imports = true
    ```

Or, with multiple root packages:

=== "INI"
    ```ini
    [importlinter]
    root_packages=
        packageone
        packagetwo
    # Optional:
    include_external_packages = True
    exclude_type_checking_imports = True
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_packages = [ "packageone", "packagetwo" ]
    # Optional:
    include_external_packages = true
    exclude_type_checking_imports = true
    ```

**Options:**

- `root_package`:
  The name of the Python package to validate. For regular packages, this must be the top level package (i.e. one with no
  dots in its name). In the special case of
  [namespace packages](https://docs.python.org/3/glossary.html#term-namespace-package), the name of the
  [portion](https://docs.python.org/3/glossary.html#term-portion) may be supplied instead, for example
  `mynamespace.foo`. If the portion is supplied, its ancestor packages will not be included in the graph.
  The `root_package` _must be importable_: usually this means it has been installed using a Python package manager,
  or it's in the current directory. (Either this or `root_packages` is required.)
- `root_packages`:
  The names of the Python packages to validate. This should be used in place of `root_package` if you want
  to analyse the imports of multiple packages, and is subject to the same requirements. (Either this or
  `root_package` is required.)
- `include_external_packages`:
  Whether to include external packages when building the import graph. Unlike root packages, external packages are
  *not* statically analyzed, so no imports from external packages will be checked. However, imports *of* external
  packages will be available for checking. Not every contract type uses this.
  For more information, see [the Grimp build_graph documentation](https://grimp.readthedocs.io/en/latest/usage.html#grimp.build_graph). (Optional.)
- `exclude_type_checking_imports`:
  Whether to exclude imports made in type checking guards. If this is `True`, any import made under an
  `if TYPE_CHECKING:` statement will not be added to the graph.
  For more information, see [the Grimp build_graph documentation](https://grimp.readthedocs.io/en/latest/usage.html#grimp.build_graph). (Optional.)

## Contracts

Additionally, you will want to define one or more [contracts](../contract_types/index.md). These take the following form:

=== "INI"
    ```ini
    [importlinter:contract:one]
    name = Contract One
    type = some_contract_type
    # (additional options)
    
    [importlinter:contract:two]
    name = Contract Two
    type = another_contract_type
    # (additional options)
    ```

=== "TOML"
    ```toml
    [[tool.importlinter.contracts]]
    name = "Contract One"
    type = "some_contract_type"
    # (additional options)

    [[tool.importlinter.contracts]]
    id = "two"  # Optional
    name = "Contract Two"
    type = "another_contract_type"
    # (additional options)
    ```

Every contract will always have the following key/value pairs:

- `name`: A human-readable name for the contract.
- `type`: The type of contract to use (see [Contract Types](../contract_types/index.md).)

Each contract type defines additional options that you supply here.

### Contract ids

It's possible to select individual contracts by id when
[running the linter with the `--contract` argument](run.md#checking-only-certain-contracts).
The way these ids are supplied depends on the configuration file format:

- *`ini` format:* each contract has its own INI section, which begins `importlinter:contract:` and ends in a
unique id (in the example above, the ids are `one` and `two`).
- *`toml` format:* ids are optional. To set one, provide an `id` (as shown in the second contract in the example above).

Contract ids must be unique within a file, and must not contain a colon (`:`).

## Using more than one configuration file

Contracts can be split across several files (for example, so that different teams can own their own contracts),
and [checked in a single run](run.md#using-multiple-configuration-files).

Each file is a complete configuration file, with its own [top level configuration](#top-level-configuration).

It's okay for [contract ids](#contract-ids) to be the same as long as they're in different configuration files.


!!! tip "Optimizing runs on multiple configuration files"

    If you are running Import Linter on a large code base using multiple configuration files,
    it can speed things up to use the same [top-level configuration](#top-level-configuration)
    across multiple files.

    This is because Import Linter will reuse the same import graph across files, if the top-level
    configuration is the same.  

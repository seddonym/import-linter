## Protected modules

*Type name:* `protected`

Protected contracts prevent modules from being directly imported, except by modules in an allow-list.
By default, descendants of each module will be checked too.

For example, if `blue` is protected, and `green` is the only module in the allow list,
then no module other than `green` (and its descendants) will be allowed to import `blue` (and its descendants) directly.

**Examples:**

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage
    
    [importlinter:contract:simple-protected-contract]
    name = Simple protected contract
    type = protected
    protected_modules =
        mypackage.protected
        mypackage.also_protected
    allowed_importers =
        mypackage.allowed
        mypackage.also_allowed
    ```
    
    ```ini
    [importlinter]
    root_package = mypackage
    
    [importlinter:contract:models-can-only-be-imported-by-colors]
    name = Models can only be imported by colors direct descendant
    type = protected
    protected_modules =
        mypackage.**.models
    allowed_importers =
        mypackage.colors.*
    ignore_imports =
        mypackage.one.green -> mypackage.one.models
        mypackage.colors.red.foo -> mypackage.three.models
    as_packages = False
    ```

=== "TOML"

    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Simple protected contract"
    type = "protected"
    protected_modules = [
        "mypackage.protected",
        "mypackage.also_protected",
    ]
    allowed_importers = [
        "mypackage.allowed",
        "mypackage.also_allowed",
    ]
    ```

    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Models can only be imported by colors direct descendant"
    type = "protected"
    protected_modules = [
        "mypackage.**.models",
    ]
    allowed_importers = [
        "mypackage.colors.*",
    ]
    ignore_imports = [
        "mypackage.one.green -> mypackage.one.models",
        "mypackage.colors.red.foo -> mypackage.three.models",
    ]
    as_packages = false
    ```

**Configuration options**

- `protected_modules`: The modules that must not be imported except by the list of allowed importers.
  If `as_packages` is `True`, descendants of a protected module are also allowed to import each other.
  For example, in the *Simple protected contract* above, `mypackage.protected.green` is allowed to import
  `mypackage.protected.blue`, but `mypackage.red` and `mypackage.also_protected.yellow` are not.
  Supports [wildcards](index.md#wildcards).
- `allowed_importers`: The only modules allowed to import the target modules. Supports [wildcards](index.md#wildcards).
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts).
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts).
- `as_packages`: Whether to treat the source and forbidden modules as packages. If `False`, each of the modules
  passed in will be treated as a module rather than a package. Default behaviour is `True` (treat modules as
  packages).


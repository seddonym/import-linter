# Forbidden

*Type name:* `forbidden`

Forbidden contracts check that one set of modules is not imported by another set of modules.

By default, descendants of each module will be checked - so if `mypackage.one` is forbidden from importing `mypackage.two`, then
`mypackage.one.blue` will be forbidden from importing `mypackage.two.green`. Indirect imports will also be checked. This
descendant behaviour can be changed by setting `as_packages` to `False`: in that case, only explicitly listed modules will be
checked, not their descendants.

External packages may also be forbidden.

**Examples:**

=== "INI"

    ```ini
    [importlinter]
    root_package = mypackage
    
    [importlinter:contract:my-forbidden-contract]
    name = My forbidden contract (internal packages only)
    type = forbidden
    source_modules =
      mypackage.one
      mypackage.two
      mypackage.three.blue
    forbidden_modules =
      mypackage.four
      mypackage.five.green
    ignore_imports =
      mypackage.one.green -> mypackage.utils
      mypackage.two -> mypackage.four
    ```

    ```ini
    [importlinter]
    root_package = mypackage
    include_external_packages = True
    
    [importlinter:contract:my-forbidden-contract]
    name = My forbidden contract (internal and external packages)
    type = forbidden
    source_modules =
      mypackage.one
      mypackage.two
    forbidden_modules =
      mypackage.three
      django
      requests
    ignore_imports =
      mypackage.one.green -> sqlalchemy
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "My forbidden contract (internal packages only)"
    type = "forbidden"
    source_modules = [
        "mypackage.one",
        "mypackage.two",
        "mypackage.three.blue",
    ]
    forbidden_modules = [
        "mypackage.four",
        "mypackage.five.green",
    ]
    ignore_imports = [
        "mypackage.one.green -> mypackage.utils",
        "mypackage.two -> mypackage.four",
    ]
    ```

    ```toml
    [tool.importlinter]
    root_package = "mypackage"
    include_external_packages = true

    [[tool.importlinter.contracts]]
    name = "My forbidden contract (internal and external packages)"
    type = "forbidden"
    source_modules = [
        "mypackage.one",
        "mypackage.two",
    ]
    forbidden_modules = [
        "mypackage.three",
        "django",
        "requests",
    ]
    ignore_imports = [
        "mypackage.one.green -> sqlalchemy",
    ]
    ```

**Configuration options**

- `source_modules`: A list of modules that should not import the forbidden modules. Supports [wildcards](index.md#wildcards).
- `forbidden_modules`: A list of modules that should not be imported by the source modules. These may include
  root level external packages (i.e. `django`, but not `django.db.models`). If external packages are included,
  the top level configuration must have `include_external_packages = True`. Supports [wildcards](index.md#wildcards).
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts).
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts).
- `allow_indirect_imports`: If `True`, allow indirect imports to forbidden modules without interpreting them
  as a reason to mark the contract broken. (Optional.)
- `as_packages`: Whether to treat the source and forbidden modules as packages. If `False`, each of the modules
  passed in will be treated as a module rather than a package. Default behaviour is `True` (treat modules as
  packages).


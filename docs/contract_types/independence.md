## Independence

*Type name:* `independence`

Independence contracts check that a set of modules do not depend on each other.

They do this by checking that there are no imports in any direction between the modules, even indirectly.

**Example:**

=== "INI"
    
    ```ini
    [importlinter:contract:my-independence-contract]
    name = My independence contract
    type = independence
    modules =
        mypackage.foo
        mypackage.bar
        mypackage.baz
    ignore_imports =
        mypackage.bar.green -> mypackage.utils
        mypackage.baz.blue -> mypackage.foo.purple
    ```

=== "TOML"
    ```toml
    [[tool.importlinter.contracts]]
    name = "My independence contract"
    type = "independence"
    modules = [
        "mypackage.foo",
        "mypackage.bar",
        "mypackage.baz",
    ]
    ignore_imports = [
        "mypackage.bar.green -> mypackage.utils",
        "mypackage.baz.blue -> mypackage.foo.purple",
    ]
    ```

**Configuration options**

- `modules`: A list of modules/subpackages that should be independent of each other. Supports [wildcards](index.md#wildcards).
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts).
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts).

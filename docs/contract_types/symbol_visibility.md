## Symbol visibility

*Type name:* `symbol_visibility`

A *symbol visibility* contract flags private (`_`-prefixed) functions, classes, and module-level
variables that are referenced from another module in the package.

This is a symbol-level rule. Import Linter's graph (and Grimp) remain module-level: the contract
uses the graph for the set of in-scope modules and for `ignore_imports`, then scans each module's
AST. Dunder names (`__all__`, `__version__`, and so on) are ignored. Importing a private *module*
is out of scope — use a [protected](protected.md) contract for that. Accessing a private attribute
on an imported class or instance is also out of scope.

The contract does **not** infer that a public name with no in-package users should be renamed to
start with `_`. That would treat user-facing API as unused.

**Examples:**

This is a violation:

```python
# mypackage/a.py
def _parse_config():
    ...

# mypackage/b.py
from mypackage.a import _parse_config
```

So is reaching the same symbol through a module object:

```python
# mypackage/b.py
from mypackage import a

a._parse_config()
```

This is allowed: `_parse_config` is only used inside `a.py`.

```python
# mypackage/a.py
def _parse_config():
    ...

def public():
    return _parse_config()

# mypackage/b.py
from mypackage.a import public
```

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage

    [importlinter:contract:visibility]
    name = Private symbols stay in their module
    type = symbol_visibility
    ignore_imports =
        mypackage.compat -> mypackage.internal
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Private symbols stay in their module"
    type = "symbol_visibility"
    ignore_imports = [
        "mypackage.compat -> mypackage.internal",
    ]
    ```

**Configuration**

- `ignore_imports`: Optional list of imports in the form `mypackage.foo -> mypackage.bar`.
  Matching edges are removed from the graph before the scan, so private-symbol references along
  those edges are not reported. Supports [wildcards](index.md#wildcards).
- `unmatched_ignore_imports_alerting`: How to report `ignore_imports` expressions that match
  nothing. Choices are `error` (default), `warn`, and `none`.

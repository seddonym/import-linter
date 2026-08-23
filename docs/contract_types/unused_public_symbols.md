## Unused public symbols

*Type name:* `unused_public_symbols`

An *unused public symbols* contract flags module-level functions, classes, and variables whose
names do not start with `_`, that no other module in the package references, and that are not
exported.

This is the rule behind “if a name is never imported, it should be private.” It is **not** the
same as “every unused public name is dead API.”

A function like `connect()` with no in-package importers may still be user-facing API. The
contract requires `_` only when all of the following hold:

1. The name is not listed in a static `__all__` (unless `respect_all` is false).
2. The defining module is not listed in `public_modules`.
3. No other module in the configured package scope references it.

`public_modules` names exact modules (or wildcard expressions). Listing `mypackage` does **not**
treat `mypackage.internal` as public. Use `mypackage.api.**` if a whole tree is the public
surface.

Import Linter's graph (and Grimp) remain module-level: the contract uses the graph for the set of
in-scope modules, then scans each module's AST. Dunder names are ignored. Names that already start
with `_` are ignored. `getattr`, `importlib`, entry points, and a non-literal `__all__` are treated
conservatively: if the contract cannot show that a name is unused and unexported, it does not
report it.

This contract does **not** flag `_`-prefixed names that are referenced from another module.

**Examples:**

This is a violation:

```python
# mypackage/a.py
def parse_internal_state():
    ...

# mypackage/b.py
# parse_internal_state is never imported
```

This is allowed, because another module uses it:

```python
# mypackage/a.py
def parse_internal_state():
    ...

# mypackage/b.py
from mypackage.a import parse_internal_state
```

This is allowed, because `connect` lives in a configured public module:

```python
# mypackage/api.py
def connect():
    ...
```

```ini
public_modules =
    mypackage.api
```

This is allowed, because `connect` is exported through a static `__all__`:

```python
# mypackage/a.py
__all__ = ["connect"]

def connect():
    ...
```

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage

    [importlinter:contract:unused-public]
    name = Unused public names should be private
    type = unused_public_symbols
    public_modules =
        mypackage
        mypackage.api
    respect_all = true
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Unused public names should be private"
    type = "unused_public_symbols"
    public_modules = [
        "mypackage",
        "mypackage.api",
    ]
    respect_all = true
    ```

**Configuration**

- `public_modules`: Optional list of modules (or wildcard expressions) whose public names are
  treated as exported API even when nothing in the package imports them. Modules are not treated
  as packages: `mypackage` does not include `mypackage.internal`.
- `respect_all`: If `true` (default), a static `__all__` of string literals marks those names as
  exported. If `__all__` is not a list or tuple of strings, every public name in that module is
  treated as exported. If `false`, `__all__` is ignored.
- `ignore_imports`: Optional list of imports in the form `mypackage.foo -> mypackage.bar`.
  Matching edges are removed from the graph before the scan. Supports [wildcards](index.md#wildcards).
  References are still collected from the AST, so this does not hide an unused public name.
- `unmatched_ignore_imports_alerting`: How to report `ignore_imports` expressions that match
  nothing. Choices are `error` (default), `warn`, and `none`.

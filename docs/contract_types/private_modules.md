## Private modules

*Type name:* `private_modules`

A *private modules* contract enforces the convention that a module whose name begins with an underscore is private
to its parent package. It may only be imported by the parent package, or by the descendants of the parent
package.

A module is private if the last component of its name starts with a single underscore. (Names like `__main__`
are not private.) The descendants of a private module are covered too, so everything inside a private package
is private.

By default a private modules contract applies to every private module in the root packages. To limit it to
some of them, use the `packages` option.

For example, with this package:

```text
mypackage/
    foo/
        _secret.py
        public.py
        sibling/
            deep.py
    bar.py
```

`mypackage.foo._secret` is private to `mypackage.foo`. These imports are allowed:

- `mypackage.foo.public -> mypackage.foo._secret` (sibling)
- `mypackage.foo.sibling.deep -> mypackage.foo._secret` (descendant of the parent, however deeply nested)
- `mypackage.foo -> mypackage.foo._secret` (the parent itself)

This one is not allowed, as `mypackage.bar` is outside the parent package:

- `mypackage.bar -> mypackage.foo._secret`

Only direct imports are checked. If `mypackage.bar` imports `mypackage.foo.public`, which imports
`mypackage.foo._secret`, that is fine.

**Examples:**

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage

    [importlinter:contract:my-contract]
    name = No private imports
    type = private_modules
    packages =
        mypackage.foo
    ignore_imports =
        mypackage.bar -> mypackage.foo._secret
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "No private imports"
    type = "private_modules"
    packages = ["mypackage.foo"]
    ignore_imports = [
        "mypackage.bar -> mypackage.foo._secret",
    ]
    ```

**Configuration options**

- `packages`: The packages whose private modules should be checked. Descendants are included, so listing
  `mypackage.foo` checks `mypackage.foo._secret`, `mypackage.foo.bar._baz` and so on. Private modules outside these
  packages are not checked. Supports [wildcards](index.md#wildcards). If not supplied, all private modules in the
  root packages are checked. (Optional.)
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts). (Optional.)
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts). (Optional.)
- `broken_contract_guidance`: See [shared options](index.md#options-used-by-multiple-contracts). (Optional.)

**Sample output**

```text
No private imports
------------------

Private modules may only be imported from within their parent package:

- mypackage.bar -> mypackage.foo._secret (l.3)
```

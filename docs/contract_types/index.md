# Contract types

Import Linter provides several contract types:

<div class="flowcard" markdown>
:material-block-helper:{ .lg .middle } __Forbidden__

---

Prevent one set of modules being imported by another.

[:octicons-arrow-right-24: Read more](forbidden.md)
</div>

<div class="flowcard" markdown>
:material-folder-arrow-left:{ .lg .middle } __Protected__

---

Prevent modules from being directly imported, except by modules in an allow-list.

[:octicons-arrow-right-24: Read more](protected.md)
</div>

<div class="flowcard" markdown>
:material-layers-triple:{ .lg .middle } __Layers__

---

Enforce a 'layered architecture'.

[:octicons-arrow-right-24: Read more](layers.md)
</div>

<div class="flowcard" markdown>
:fontawesome-solid-grid-horizontal:{ .lg .middle } __Independence__

---

Prevent a set of modules depending on each other.

[:octicons-arrow-right-24: Read more](independence.md)  
</div>

<div class="flowcard" markdown>
:material-graph-outline:{ .lg .middle } __Acyclic siblings__

---

Forbid dependency cycles between siblings.

[:octicons-arrow-right-24: Read more](acyclic_siblings.md)
</div>

## Custom contract types

If none of the built in contract types meets your needs, you can define a custom contract type: see
[Custom Contract Types](../custom_contract_types.md).

## Options used by multiple contracts

- `ignore_imports`: Optional list of imports, each in the form `mypackage.foo.importer -> mypackage.bar.imported`.
  These imports will be ignored: if the import would cause a contract to be broken, adding it to the list will cause the
  contract be kept instead. Supports [wildcards](index.md#wildcards).

- `unmatched_ignore_imports_alerting`: The alerting level for handling expressions supplied in `ignore_imports`
  that do not match any imports in the graph. Choices are:

    - `error`: Error if there are any unmatched expressions (default).
    - `warn`: Print a warning for each unmatched expression.
    - `none`: Do not alert.

- `broken_contract_guidance`: Optional lines of text explaining how to fix the contract. If the contract is broken, these are
  displayed after its violations. Use this to signpost the right way to do something, so whoever broke the contract
  doesn't have to read the contract definition to find out.

    This is particularly useful when migrating from one system to another: a contract can forbid the old system
    while pointing at the new one, so the reader knows what to do instead of adding another entry to the
    `ignore_imports` burndown list.

    ```toml
    [[tool.importlinter.contracts]]
    name = "Colors should not use the legacy numbers API"
    type = "forbidden"
    source_modules = ["mypackage.colors"]
    forbidden_modules = ["mypackage.legacy.numbers"]
    broken_contract_guidance = """
    Use mypackage.numbers instead - it's the supported top-level interface.
    Migration guide: https://docs.example.com/numbers-migration
    """
    ```

    ```ini
    [importlinter:contract:no-legacy-colors]
    name = Colors should not use the legacy numbers API
    type = forbidden
    source_modules =
        mypackage.colors
    forbidden_modules =
        mypackage.legacy.numbers
    broken_contract_guidance =
        Use mypackage.numbers instead - it's the supported top-level interface.
        Migration guide: https://docs.example.com/numbers-migration
    ```

    When this contract is broken, the output ends with:

    ```
    Use mypackage.numbers instead - it's the supported top-level interface.
    Migration guide: https://docs.example.com/numbers-migration
    ```

    Each line is displayed as written, so any formatting (such as bullets) is up to you.

## Wildcards

Many contract fields refer to sets of modules - some (but not all) of these support wildcards.

`*` stands in for a module name, without including subpackages. `**` includes subpackages too.

Examples:

- `mypackage.*`: matches `mypackage.foo` but not `mypackage.foo.bar`.
- `mypackage.*.baz`: matches `mypackage.foo.baz` but not `mypackage.foo.bar.baz`.
- `mypackage.*.*`: matches `mypackage.foo.bar` and `mypackage.foobar.baz`.
- `mypackage.**`: matches `mypackage.foo.bar` and `mypackage.foo.bar.baz`.
- `mypackage.**.qux`: matches `mypackage.foo.bar.qux` and `mypackage.foo.bar.baz.qux`.
- `mypackage.foo*`: not a valid expression. (The wildcard must replace a whole module name.)

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

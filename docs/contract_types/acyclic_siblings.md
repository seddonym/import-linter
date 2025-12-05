## Acyclic siblings

*Type name:* `acyclic_siblings`

An *acyclic siblings* contract forbids dependency cycles between siblings. The direct imports between them (and their
descendants) are treated as dependencies; if a cycle exists between these dependencies then the contract will fail. The
contract begins by checking the children of the supplied ancestors. Then it repeats down the generations,
drilling into each subpackage and checking those children for cycles.

This is easier to understand with a diagram. Take this package (the arrows represent imports):

![Diagram showing cycles between siblings](../img/acyclic-siblings.svg)

While no direct cycles exist between individual Python modules, an `acyclic_siblings` contract running on
`mypackage` will detect a cycle between the children of `mypackage`: `blue` depends on `green`, which depends
on `red`, which depends on `yellow`, which depends on `blue`. When it drills down a generation, it will also
find a cycle between the children of `blue`.

How many generations are drilled down into is controlled by an optional `depth` argument (which defaults to 10).
If `depth` is 0, only children of the ancestors will be checked; in the example above, the cycle
between `blue`, `green`, `red` and `yellow` will be detected (assuming the supplied ancestor is `mypackage`)
but not the cycle between `blue`'s children. With a `depth` of 1, that cycle will be found too.

Drilldown can be skipped for specific descendants using the `skip_descendants` argument (see below).

**Important:** neither the `depth` or `skip_descendants` options prevent deeper imports from being considered when
analyzing children in earlier generations. So if `.blue.some.deep.module` imports `.green.another.deep.module`, that could still
contribute to a cycle between `.blue` and `.green`, even if the `depth` is 0 or `.green.another` is listed
as a skipped descendant. If you want to ignore an import altogether, use `ignore_imports` instead.

**Examples:**

=== "INI"
    ```ini
    [importlinter]
    root_package = mypackage
    
    [importlinter:contract:my-contract]
    name = Minimal acyclic siblings contract
    type = acyclic_siblings
    ancestors = mypackage
    
    [importlinter:contract:my-contract]
    name = Acyclic siblings contract with more options
    type = acyclic_siblings
    ancestors =
        mypackage.foo
        mypackage.bar.*
    depth = 5
    skip_descendants =
        mypackage.foo.purple
        mypackage.foo.**.orange
    ignore_imports =
        mypackage.foo.blue.one -> mypackage.foo.green.two
    ```

=== "TOML"
    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Minimal acyclic siblings contract"
    type = "acyclic_siblings"
    ancestors = ["mypackage"]

    [[tool.importlinter.contracts]]
    name = "Acyclic siblings contract with more options"
    type = "acyclic_siblings"
    ancestors = [
        "mypackage.foo",
        "mypackage.bar.*",
    ]
    depth = 5
    skip_descendants = [
        "mypackage.foo.purple",
        "mypackage.foo.**.orange",
    ]
    ignore_imports = [
        "mypackage.foo.blue.one -> mypackage.foo.green.two",
    ]
    ```

**Configuration options**

- `ancestors`: The packages whose descendants should be checked for cycles.
  Supports [wildcards](index.md#wildcards).
- `depth`: How many generations of siblings to check, relative to the ancestors. A depth of 0 will only check the
  children, depth 1 will check grandchildren (as sets of siblings), etc. Can be an integer >=0. Default 10.
  (Optional.)
- `skip_descendants`: The ancestors of children that shouldn't be checked. For example, if
  `mypackage.foo.purple` is a skipped descendant, then the children of that package won't be checked for cycles,
  nor will their descendants. Supports [wildcards](index.md#wildcards). (Optional.)
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts). (Optional.)
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts). (Optional.)

**Sample output**

```text
Broken acyclic_siblings contract
--------------------------------

No cycles are allowed in mypackage.foo.
It could be made acyclic by removing 1 dependency:

- .alpha -> .beta (3 imports)

No cycles are allowed in mypackage.foo.alpha.
It could be made acyclic by removing 11 dependencies:

- .blue -> .green (4 imports)
- .blue -> .yellow (11 imports)
- .green -> .orange (1 import)
- .purple -> .red (3 imports)
- .purple -> .yellow (2 imports)
(and 6 more).
```


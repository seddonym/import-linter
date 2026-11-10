## Encapsulated modules

_Type name:_ `encapsulated`

Encapsulated contracts treat a set of modules as a single unit, and prevent imports across its boundary
except in the ways you allow:

- The unit must not import any other module in your project, except for the modules it's allowed to import.
- Other modules must not import the unit, except for its public modules.

The unit is made up of the listed `modules` and all of their descendants. The modules don't have to be next to each
other, so you can keep a feature together as one unit even when it is split across the layers of your project.

For example, a billing feature might be split between a data layer and a domain layer:

```text
mypackage/
    data/
        billing/
        orders/
    domain/
        billing/
            api.py
        orders/
```

If `mypackage.data.billing` and `mypackage.domain.billing` are encapsulated together, with
`mypackage.domain.billing.api` as their only public module, then:

- Modules in `mypackage.data.billing` and `mypackage.domain.billing` may import each other.
- Neither may import anything else in `mypackage`, such as `mypackage.data.orders`.
- Modules outside the unit may import `mypackage.domain.billing.api` (and its descendants), but not the rest of the
  unit.

These rules apply to every root package of your project. Imports of external packages are not affected.

If the unit may use some other modules in your project, such as shared utilities, list them in `allow_imports_to`.
This only affects imports out of the unit: those modules still can't import the unit, except for its public modules.

Only direct imports are checked. An indirect import always begins or ends with a direct import across the boundary of
the unit, and that is what will be reported.

To allow exceptions, use `ignore_imports`.

**Examples:**

=== "INI"

    ```ini
    [importlinter]
    root_package = mypackage

    [importlinter:contract:orders-are-encapsulated]
    name = Orders are encapsulated
    type = encapsulated
    modules =
        mypackage.orders
    public_modules =
        mypackage.orders.api
    ```

    ```ini
    [importlinter]
    root_package = mypackage

    [importlinter:contract:billing-is-encapsulated]
    name = Billing is encapsulated
    type = encapsulated
    modules =
        mypackage.data.billing
        mypackage.domain.billing
    public_modules =
        mypackage.domain.billing.api
    allow_imports_to =
        mypackage.utils
    ignore_imports =
        mypackage.checkout.views -> mypackage.domain.billing.models
    ```

=== "TOML"

    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Orders are encapsulated"
    type = "encapsulated"
    modules = [
        "mypackage.orders",
    ]
    public_modules = [
        "mypackage.orders.api",
    ]
    ```

    ```toml
    [tool.importlinter]
    root_package = "mypackage"

    [[tool.importlinter.contracts]]
    name = "Billing is encapsulated"
    type = "encapsulated"
    modules = [
        "mypackage.data.billing",
        "mypackage.domain.billing",
    ]
    public_modules = [
        "mypackage.domain.billing.api",
    ]
    allow_imports_to = [
        "mypackage.utils",
    ]
    ignore_imports = [
        "mypackage.checkout.views -> mypackage.domain.billing.models",
    ]
    ```

**Configuration options**

- `modules`: The modules that make up the unit. Descendants of each module are also part of the unit. The modules
  don't need to be next to each other.
  Each module must exist. Supports [wildcards](index.md#wildcards).
- `public_modules`: Modules within the unit that other modules are allowed to import. Descendants of each module are
  also public. Each public module must be within the unit. If this is omitted, other modules may not import the unit at
  all. (Optional.) Supports [wildcards](index.md#wildcards).
- `allow_imports_to`: Modules outside the unit that the unit is allowed to import, such as common utilities.
  Descendants of each module are also allowed. Supports [wildcards](index.md#wildcards).
- `ignore_imports`: See [shared options](index.md#options-used-by-multiple-contracts).
- `unmatched_ignore_imports_alerting`: See [shared options](index.md#options-used-by-multiple-contracts).
- `broken_contract_guidance`: See [shared options](index.md#options-used-by-multiple-contracts).

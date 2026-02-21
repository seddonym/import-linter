# Interactive UI

Import Linter provides a local browser-based interface that you can use to explore the architecture
of any installed Python package. This is what it looks like when visualizing the `django.db` package:

![Screenshot of the Import Linter UI](img/ui-screenshot.png)

## Installation

The UI requires the `ui` extra. Install it alongside `import-linter`:

=== "pip"
    ```console
    pip install import-linter[ui]
    ```

=== "uv"
    ```console
    uv add --dev import-linter[ui]
    ```

=== "poetry"
    ```console
    poetry add import-linter[ui] --group dev
    ```

## Launching the UI

Run `import-linter explore`, passing the name of the module you want to explore:

```console
import-linter explore mypackage
```

This will start a local web server and open your browser. The module must be importable
from the current directory.

You can also pass a subpackage to start deeper in the hierarchy:

```console
import-linter explore mypackage.subpackage
```

## Navigating the graph

The graph shows the dependencies between all the immediate children of the package you're viewing.

An arrow can be read as saying "depends on". If package `one` points to `two`, then at least one module in `one` imports a module in `b`.

!!! example

    In the example above, there is an arrow from `.models` to `.utils`. This is because (along with one other import)
    `django.db.models.constraints` imports `django.db.utils.DEFAULT_DB_ALIAS`.

### Drilling down

Click on any package node in the graph to drill down into it and see its children.
Only packages (modules that contain submodules) are clickable.

## Options

The right sidebar provides options to customize the visualization.

### Import totals

Enabling **Import totals** labels each arrow with the total number of individual import statements
it represents.

![Screenshot of import totals](img/ui-import-totals.png)

Here you can see that there are two imports from modules within `.models` of modules within `.utils`.

### Cycle breakers

Enabling **Cycle breakers** highlights (with a dashed line) a minimal set of dependencies that,
if removed, would make the graph acyclic.

![Screenshot of cycle breakers](img/ui-cycle-breakers.png)

Here you can see that two of the dependencies are shown as a dashed line. If these dependencies were to be removed,
the graph would be acyclic. To decide on the cycle breakers, Import Linter uses the [nominate_cycle_breakers method provided by Grimp](https://grimp.readthedocs.io/en/stable/usage.html#ImportGraph.nominate_cycle_breakers).

## Drawing graphs on the command line

If you'd prefer to get the raw graph data rather than using the interactive UI,
you can use `import-linter drawgraph` to output a graph in
[DOT format](https://en.wikipedia.org/wiki/DOT_(graph_description_language)) to stdout:

```console
import-linter drawgraph mypackage
```

This can be piped to Graphviz or any other tool that accepts DOT input:

```console
import-linter drawgraph mypackage | dot -Tpng -o graph.png
```

The same display options are available as flags:

```console
import-linter drawgraph mypackage --show-import-totals
import-linter drawgraph mypackage --show-cycle-breakers
```

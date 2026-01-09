"""FastAPI server for the interactive graph explorer."""

from __future__ import annotations

import logging
import os
import sys
import time
import webbrowser
from pathlib import Path

import click
import grimp
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from impulse.application.use_cases import _build_dot

from importlinter import api as importlinter_api
from importlinter.application import use_cases
from importlinter.application.use_cases import _register_contract_types

logger = logging.getLogger(__name__)

app = FastAPI(title="Import Linter Explorer")

STATIC_DIR = Path(__file__).parent / "static"

# Global state for the initial module (only used for default request)
_initial_module: str | None = None
_config_filename: str | None = None


def _get_top_level_package(module_name: str) -> str:
    """Extract the top-level package name from a module path."""
    return module_name.split(".")[0]


def _build_graph_for_module(
    module_name: str,
    show_import_totals: bool = False,
    show_cycle_breakers: bool = False,
) -> tuple[str, list[str]]:
    """Build the DOT graph for a given module using impulse.

    Returns:
        A tuple of (dot_string, packages) where packages is a list of
        child module names that have their own children (i.e., are packages).
    """
    logger.info(f"Building graph for module: {module_name}")
    start_time = time.time()

    top_level_package = _get_top_level_package(module_name)
    logger.debug(f"Building grimp graph for top-level package: {top_level_package}")
    grimp_graph = grimp.build_graph(top_level_package)
    logger.debug(f"Grimp graph built in {time.time() - start_time:.2f}s")

    # Find which children are packages (have their own children)
    children = grimp_graph.find_children(module_name)
    packages = []
    for child in children:
        grandchildren = grimp_graph.find_children(child)
        if grandchildren:
            # This child has children, so it's a package
            # Store the relative name (e.g., ".adapters")
            relative_name = "." + child.split(".")[-1]
            packages.append(relative_name)

    dot_graph = _build_dot(
        grimp_graph=grimp_graph,
        module_name=module_name,
        show_import_totals=show_import_totals,
        show_cycle_breakers=show_cycle_breakers,
    )
    total_time = time.time() - start_time
    logger.info(f"Graph for {module_name} built in {total_time:.2f}s ({len(packages)} packages)")
    return dot_graph.render(), packages


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """Serve the main HTML page."""
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/logo.svg")
async def logo() -> HTMLResponse:
    """Serve the logo SVG."""
    # Navigate from src/importlinter/interactive to docs/img
    logo_path = (
        Path(__file__).parent.parent.parent.parent
        / "docs"
        / "img"
        / "import-linter-logo-square.svg"
    )
    return HTMLResponse(content=logo_path.read_text(), media_type="image/svg+xml")


@app.get("/api/graph")
async def get_graph(
    module: str | None = None,
    show_import_totals: bool = False,
    show_cycle_breakers: bool = False,
) -> dict:
    """Return the graph data in DOT format for the specified module."""
    if module is None:
        module = _initial_module

    if module is None:
        return {"error": "No module specified"}

    try:
        dot, packages = _build_graph_for_module(
            module,
            show_import_totals=show_import_totals,
            show_cycle_breakers=show_cycle_breakers,
        )
        return {"dot": dot, "module": module, "packages": packages}
    except Exception as e:
        return {"error": str(e)}


def _format_contract_config(contract_options: dict) -> str:
    """Format contract options as an INI-style config string."""
    name = contract_options.get("name", "")
    # Create a slug from the name for the section header
    slug = name.lower().replace(" ", "-")
    lines = [f"[importlinter:contract:{slug}]"]
    for key, value in contract_options.items():
        if isinstance(value, list):
            # Multi-line value
            lines.append(f"{key} =")
            for item in value:
                lines.append(f"    {item}")
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines)


@app.get("/api/contracts")
async def get_contracts() -> dict:
    """Return the contracts from the configuration file."""
    print(f"Loading contract config: {_config_filename}.")
    try:
        config_data = importlinter_api.read_configuration(_config_filename)
        contracts = []
        for contract_options in config_data["contracts_options"]:
            contract_id = contract_options.get("id", "unknown")
            contract_name = contract_options.get("name", "Unnamed")
            contract_type = contract_options.get("type", "unknown")
            contracts.append(
                {
                    "id": contract_id,
                    "name": contract_name,
                    "type": contract_type,
                    "config": _format_contract_config(contract_options),
                }
            )
        return {
            "contracts": contracts,
            "session_options": config_data["session_options"],
            "config_filename": _config_filename,
        }
    except FileNotFoundError:
        print("File not found.")
        return {"error": "No configuration file found", "contracts": [], "config_filename": _config_filename}
    except Exception as e:
        print(f"Error: {e}.")
        return {"error": str(e), "contracts": [], "config_filename": _config_filename}


@app.post("/api/contracts/{contract_id}/check")
async def check_contract(contract_id: str) -> dict:
    """Check a specific contract and return the results."""
    print(f"Checking contract: {contract_id}")
    start_time = time.time()

    try:
        # Create the report by running the contract
        user_options = use_cases.read_user_options(_config_filename)
        _register_contract_types(user_options)
        report = use_cases.create_report(
            user_options=user_options,
            limit_to_contracts=(contract_id,),
            cache_dir=None,  # Don't use cache for interactive runs
            show_timings=False,
            verbose=False,
        )

        # Find the contract check result
        for contract, check in report.get_contracts_and_checks():
            if contract.contract_options.get("id") == contract_id:
                duration = time.time() - start_time
                violations = _extract_violations(contract, check)
                return {
                    "contract_id": contract_id,
                    "kept": check.kept,
                    "violations": violations,
                    "warnings": check.warnings,
                    "duration": round(duration, 2),
                }

        return {"error": f"Contract '{contract_id}' not found in results"}

    except Exception as e:
        print(f"Error checking contract: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def _extract_violations(contract, check) -> list[dict]:
    """Extract violations from a contract check into a frontend-friendly format."""
    violations = []
    metadata = check.metadata or {}

    # Handle different metadata formats based on contract type

    # Layers contract - invalid_dependencies
    if "invalid_dependencies" in metadata:
        for dep in metadata["invalid_dependencies"]:
            higher_layer = dep.get("higher_layer", "")
            lower_layer = dep.get("lower_layer", "")
            chains = dep.get("chains", [])

            import_count = sum(len(chain) for chain in chains)

            violations.append({
                "importer": f"{higher_layer} (higher layer)",
                "imported": f"{lower_layer} (lower layer)",
                "count": import_count,
                "chains": chains,
            })

    # Layers contract - undeclared modules (warning, not violation per se)
    if "undeclared_modules" in metadata:
        undeclared = metadata["undeclared_modules"]
        if undeclared:
            violations.append({
                "importer": ", ".join(sorted(undeclared)),
                "imported": "(undeclared modules)",
                "count": len(undeclared),
            })

    # Forbidden, Independence contracts - invalid_chains
    if "invalid_chains" in metadata:
        for chain_info in metadata["invalid_chains"]:
            upstream = chain_info.get("upstream_module", "")
            downstream = chain_info.get("downstream_module", "")
            chains = chain_info.get("chains", [])

            # Count total imports across all chains
            import_count = sum(len(chain) for chain in chains)

            violations.append({
                "importer": downstream,
                "imported": upstream,
                "count": import_count,
                "chains": chains,
            })

    # Protected contract - invalid_imports
    if "invalid_imports" in metadata:
        for import_info in metadata["invalid_imports"]:
            violations.append({
                "importer": import_info.get("importer", ""),
                "imported": import_info.get("imported", ""),
                "count": 1,
            })

    # Acyclic contracts - cycles
    if "cycles" in metadata:
        for cycle in metadata["cycles"]:
            cycle_str = " → ".join(cycle) + " → " + cycle[0]
            violations.append({
                "importer": cycle_str,
                "imported": "(cycle)",
                "count": len(cycle),
            })

    return violations


@click.command()
@click.option("--config", default=None, help="The config file to use.")
@click.argument("module_name")
def main(config: str | None, module_name: str) -> None:
    """
    Launch the interactive import graph explorer.

    MODULE_NAME is the Python module to visualize (e.g., 'importlinter').
    """
    global _initial_module, _config_filename

    _config_filename = config

    port = 8000
    url = f"http://localhost:{port}"
    print(f"Launching interactive import graph explorer for {config}.")
    print(f"Building import graph for '{module_name}'...")

    # Insert current directory into sys.path for module resolution
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    # Verify the module can be graphed
    top_level_package = _get_top_level_package(module_name)
    try:
        grimp.build_graph(top_level_package)
    except Exception as e:
        print(f"Error building graph: {e}")
        raise click.Abort()

    # Store initial module for default requests
    _initial_module = module_name

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    print(f"Starting Import Linter Explorer at {url}")
    print("Press Ctrl+C to stop the server")

    # Open browser after a short delay (server needs to start first)
    import threading

    threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()

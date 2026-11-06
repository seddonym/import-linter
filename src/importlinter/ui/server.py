from __future__ import annotations
from typing import cast
import json
import logging
import os
import socket
import sys
import webbrowser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import uvicorn.logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import dataclasses
from typing_extensions import TypedDict

from importlinter.ui.explorer import generate_dot

STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger(__name__)

LOCALHOST = "localhost"


class GraphResponse(TypedDict):
    dot_string: str
    module: str
    child_packages: list[str]


class ErrorResponse(TypedDict):
    error: str


def launch(module_names: list[str]) -> None:
    """
    Launch the interactive UI in a local browser.

    Args:
        module_names: The Python modules to explore. If more than one is supplied, the UI opens
            on a top-level overview showing the packages and the dependencies between them.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        uvicorn.logging.ColourizedFormatter("%(levelprefix)s %(message)s", use_colors=True)
    )
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)

    # Add current directory to Python path, making it more likely we'll
    # be able to import the package.
    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    root_packages = [module_name.split(".")[0] for module_name in module_names]
    for top_level_package in root_packages:
        try:
            __import__(top_level_package)
        except ImportError:
            logger.error(
                f"Could not import '{top_level_package}'. "
                f"Make sure the package is installed or the current directory contains it."
            )
            sys.exit(1)

    # A single module opens directly on that module; several open on the overview.
    initial_module = module_names[0] if len(module_names) == 1 else ""

    port = _find_free_port()
    app = create_app(
        root_packages=root_packages,
        initial_module=initial_module,
        browser_url=f"http://{LOCALHOST}:{port}",
    )
    uvicorn.run(app, host=LOCALHOST, port=port, access_log=False)


def create_app(
    root_packages: list[str] | None = None,
    initial_module: str = "",
    browser_url: str | None = None,
) -> FastAPI:
    """
    Return FastAPI application for the interactive UI.

    Args:
        root_packages: The root packages whose combined graph is being explored.
        initial_module: The module to display on load (empty for the top-level overview).
        browser_url: The URL to open in a browser once the app is ready.
    """
    root_packages = list(root_packages or [])

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if browser_url:
            webbrowser.open(browser_url)
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.root_packages = root_packages
    app.state.initial_module = initial_module
    app.state.grimp_cache = {}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text()
        html = html.replace("{{root_packages_json}}", json.dumps(request.app.state.root_packages))
        html = html.replace(
            "{{initial_module_json}}", json.dumps(request.app.state.initial_module)
        )
        return HTMLResponse(content=html)

    def _build_graph_response(
        request: Request,
        module: str,
        show_import_totals: bool,
        show_module_counts: bool,
        show_lazy_imports: bool,
        show_cycle_breakers: bool,
    ) -> GraphResponse | ErrorResponse:
        try:
            graph_data = generate_dot(
                request.app.state.grimp_cache,
                module,
                show_import_totals,
                show_module_counts,
                show_lazy_imports,
                show_cycle_breakers,
                request.app.state.root_packages,
            )
            return cast(GraphResponse, dataclasses.asdict(graph_data))
        except Exception as e:
            logger.exception(f"Error building graph for '{module}'")
            return {"error": str(e)}

    @app.get("/api/graph")
    def get_overview_graph(
        request: Request,
        show_import_totals: bool = False,
        show_module_counts: bool = False,
        show_lazy_imports: bool = False,
        show_cycle_breakers: bool = False,
    ) -> GraphResponse | ErrorResponse:
        return _build_graph_response(
            request,
            "",
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
        )

    @app.get("/api/graph/{module:path}")
    def get_graph(
        request: Request,
        module: str,
        show_import_totals: bool = False,
        show_module_counts: bool = False,
        show_lazy_imports: bool = False,
        show_cycle_breakers: bool = False,
    ) -> GraphResponse | ErrorResponse:
        return _build_graph_response(
            request,
            module,
            show_import_totals,
            show_module_counts,
            show_lazy_imports,
            show_cycle_breakers,
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOCALHOST, 0))
        return s.getsockname()[1]

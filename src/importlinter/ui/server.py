from __future__ import annotations
from typing import cast
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


def launch(module_name: str) -> None:
    """
    Launch the interactive UI in a local browser.
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

    top_level_package = module_name.split(".")[0]
    try:
        __import__(top_level_package)
    except ImportError:
        logger.error(
            f"Could not import '{top_level_package}'. "
            f"Make sure the package is installed or the current directory contains it."
        )
        sys.exit(1)

    port = _find_free_port()
    app = create_app(module_name=module_name, browser_url=f"http://{LOCALHOST}:{port}")
    uvicorn.run(app, host=LOCALHOST, port=port, access_log=False)


def create_app(
    module_name: str = "",
    browser_url: str | None = None,
) -> FastAPI:
    """
    Return FastAPI application for the interactive UI.

    Args:
        module_name: The Python module being explored.
        browser_url: The URL to open in a browser once the app is ready.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if browser_url:
            webbrowser.open(browser_url)
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.module_name = module_name
    app.state.grimp_cache = {}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        html = (STATIC_DIR / "index.html").read_text()
        html = html.replace("{{module_name}}", request.app.state.module_name)
        return HTMLResponse(content=html)

    @app.get("/api/graph/{module:path}")
    def get_graph(
        request: Request,
        module: str,
        show_import_totals: bool = False,
        show_cycle_breakers: bool = False,
    ) -> GraphResponse | ErrorResponse:
        try:
            graph_data = generate_dot(
                request.app.state.grimp_cache, module, show_import_totals, show_cycle_breakers
            )
            return cast(GraphResponse, dataclasses.asdict(graph_data))
        except Exception as e:
            logger.exception(f"Error building graph for '{module}'")
            return {"error": str(e)}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    return app


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((LOCALHOST, 0))
        return s.getsockname()[1]

"""Serve the single-page shell for every page URL, so refresh and pasted links work.

The shell carries no data. Whether you may see anything is decided by the API.
"""

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

PAGES = [re.compile(p) for p in (r"^login$", r"^signup$", r"^visits$", r"^visits/[^/]+$", r"^admin/users$")]
ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def install_pages(app: FastAPI, static_dir: Path) -> None:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    shell = static_dir / "index.html"

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/visits")

    @app.api_route("/api/{rest:path}", methods=ALL_METHODS, include_in_schema=False)
    def unknown_api(rest: str):
        # Keeps unknown API paths a JSON 404 for every method, rather than falling into the page catch-all.
        raise HTTPException(404)

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str):
        known = any(p.match(path) for p in PAGES)
        # Unknown pages still get the shell, so the app can show a proper "Page not found", with a real 404 status.
        return FileResponse(shell, status_code=200 if known else 404)

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import settings
from app.api.routes import router
from app.storage.json_store import JsonStore

app = FastAPI(title="AI Job Assistant API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8443", "http://localhost:8444", "http://127.0.0.1:8443", "http://127.0.0.1:8444"], allow_methods=["*"], allow_headers=["*"])
app.state.store = JsonStore(settings.DATA_DIR)
app.include_router(router)
FRONTEND_DIST = settings.PROJECT_ROOT / "frontend" / "dist"


@app.get("/")
def root():
    index = FRONTEND_DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"name": "AI Job Assistant API", "docs": "/docs", "health": "/api/health"}


@app.get("/{asset_path:path}", include_in_schema=False)
def frontend_route(asset_path: str):
    if not FRONTEND_DIST.is_dir() or asset_path == "api" or asset_path.startswith("api/"):
        raise HTTPException(404, "Not found")
    root = FRONTEND_DIST.resolve()
    requested = (root / asset_path).resolve()
    if requested.is_relative_to(root) and requested.is_file():
        return FileResponse(requested)
    index = root / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(404, "Not found")

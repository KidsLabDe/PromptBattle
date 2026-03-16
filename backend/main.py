from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.routes import game, ws
from backend.services.image_generator import load_flux
from backend.services.similarity import load_clip


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load models at startup
    load_clip()
    load_flux()
    yield


app = FastAPI(title="Prompt Battle", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(game.router)
app.include_router(ws.router)

# Serve frontend static files if build exists
static_dir = settings.static_dir
if static_dir.exists():
    app.mount("/_app", StaticFiles(directory=str(static_dir / "_app")), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """SPA fallback: serve index.html for all non-API/non-WS routes."""
        file_path = static_dir / full_path
        no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate"}
        if file_path.is_file():
            # Immutable assets (hashed filenames) can be cached forever
            if "/_app/immutable/" in str(file_path):
                return FileResponse(file_path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(file_path, headers=no_cache)
        return FileResponse(static_dir / "index.html", headers=no_cache)

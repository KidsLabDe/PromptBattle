from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

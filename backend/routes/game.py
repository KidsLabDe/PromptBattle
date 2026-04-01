from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.config import settings
from backend.game_state import create_game, get_game
from backend.models import (
    GameMode,
    GameStateResponse,
    StartGameRequest,
    StartGameResponse,
)
from backend.services.target_images import pick_random_target, target_image_path

router = APIRouter(prefix="/api")


@router.get("/config")
async def get_config():
    """Return frontend-relevant timing configuration."""
    return {
        "image_display_seconds": settings.image_display_seconds,
        "compare_bar_seconds": settings.compare_bar_seconds,
        "score_reveal_seconds": settings.score_reveal_seconds,
        "result_display_seconds": settings.result_display_seconds,
        "round_time_seconds": settings.round_time_seconds,
        "lobby_timeout_seconds": settings.lobby_timeout_seconds,
        "gameover_restart_seconds": settings.gameover_restart_seconds,
        "display_password_required": bool(settings.display_password),
    }


class DisplayLoginRequest(BaseModel):
    password: str


@router.post("/display/login")
async def display_login(req: DisplayLoginRequest):
    """Validate display password."""
    if not settings.display_password:
        return {"valid": True}
    if req.password == settings.display_password:
        return {"valid": True}
    raise HTTPException(403, "Falsches Passwort")


@router.post("/game/start", response_model=StartGameResponse)
async def start_game(req: StartGameRequest | None = None):
    mode = req.mode if req else GameMode.SINGLE
    game = create_game(mode=mode)
    target = pick_random_target()
    game.start_round(target)

    return StartGameResponse(
        game_id=game.game_id,
        mode=game.mode,
        target_image=target,
        round=game.round,
        threshold=game.threshold,
        time_seconds=game.time_remaining,
        join_token=game.join_token if mode == GameMode.MULTI else None,
    )


@router.get("/game/{game_id}/state", response_model=GameStateResponse)
async def get_game_state(game_id: str):
    game = get_game(game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    return GameStateResponse(
        game_id=game.game_id,
        status=game.status,
        round=game.round,
        threshold=game.threshold,
        time_remaining=game.time_remaining,
        history=game.history,
    )


@router.get("/game/{game_id}/player/{token}")
async def validate_player(game_id: str, token: str):
    game = get_game(game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    # Check if token is the join token (valid for joining)
    if token == game.join_token:
        return {
            "valid": True,
            "game_id": game_id,
            "status": game.status,
            "round": game.round,
        }
    # Check if already assigned player token
    player = game.get_player_by_token(token)
    if player is None:
        raise HTTPException(403, "Invalid player token")
    return {
        "player": player,
        "game_id": game_id,
        "status": game.status,
        "round": game.round,
    }


@router.get("/images/target/{filename}")
async def serve_target_image(filename: str):
    path = target_image_path(filename)
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)

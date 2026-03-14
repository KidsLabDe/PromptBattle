from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.game_state import create_game, get_game
from backend.models import (
    GameMode,
    GameStateResponse,
    StartGameRequest,
    StartGameResponse,
)
from backend.services.target_images import pick_random_target, target_image_path

router = APIRouter(prefix="/api")


@router.post("/game/start", response_model=StartGameResponse)
async def start_game(req: StartGameRequest | None = None):
    mode = req.mode if req else GameMode.SINGLE
    game = create_game(mode=mode)
    target = pick_random_target()
    game.start_round(target)

    player_tokens = None
    if mode == GameMode.MULTI:
        player_tokens = {
            str(k): v for k, v in game.player_tokens.items()
        }

    return StartGameResponse(
        game_id=game.game_id,
        mode=game.mode,
        target_image=target,
        round=game.round,
        threshold=game.threshold,
        time_seconds=game.time_remaining,
        player_tokens=player_tokens,
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

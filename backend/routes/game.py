from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.game_state import create_game, get_game
from backend.models import (
    GameStateResponse,
    StartGameResponse,
    SubmitPromptRequest,
)
from backend.services.target_images import pick_random_target, target_image_path

router = APIRouter(prefix="/api")


@router.post("/game/start", response_model=StartGameResponse)
async def start_game():
    game = create_game()
    target = pick_random_target()
    game.start_round(target)
    return StartGameResponse(
        game_id=game.game_id,
        target_image=target,
        round=game.round,
        threshold=game.threshold,
        time_seconds=game.time_remaining,
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


@router.get("/images/target/{filename}")
async def serve_target_image(filename: str):
    path = target_image_path(filename)
    if not path.exists():
        raise HTTPException(404, "Image not found")
    return FileResponse(path)

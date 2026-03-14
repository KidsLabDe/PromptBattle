from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    GENERATING = "generating"
    RESULT = "result"
    GAME_OVER = "game_over"


class StartGameResponse(BaseModel):
    game_id: str
    target_image: str
    round: int
    threshold: float
    time_seconds: int


class SubmitPromptRequest(BaseModel):
    prompt: str


class RoundResult(BaseModel):
    round: int
    prompt: str
    score: float
    threshold: float
    passed: bool
    generated_image: str  # base64
    target_image: str


class ScoreResult(BaseModel):
    score: float
    threshold: float
    passed: bool
    generated_image: str  # base64
    round: int


class GameStateResponse(BaseModel):
    game_id: str
    status: GameStatus
    round: int
    threshold: float
    time_remaining: int
    history: list[RoundResult]


class WSMessage(BaseModel):
    type: str
    data: dict | None = None

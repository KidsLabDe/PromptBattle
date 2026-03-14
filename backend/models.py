from __future__ import annotations

from enum import Enum
from pydantic import BaseModel


class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    GENERATING = "generating"
    RESULT = "result"
    GAME_OVER = "game_over"


class GameMode(str, Enum):
    SINGLE = "single"
    MULTI = "multi"


class StartGameRequest(BaseModel):
    mode: GameMode = GameMode.SINGLE


class StartGameResponse(BaseModel):
    game_id: str
    mode: GameMode
    target_image: str
    round: int
    threshold: float
    time_seconds: int
    player_tokens: dict[str, str] | None = None


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


class PlayerResult(BaseModel):
    player: int
    prompt: str
    score: float
    generated_image: str


class MultiRoundResult(BaseModel):
    round: int
    target_image: str
    player1: PlayerResult
    player2: PlayerResult
    winner: int  # 1, 2, or 0 for tie


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

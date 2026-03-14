from __future__ import annotations

import asyncio
import time
import uuid

from backend.config import settings
from backend.models import GameStatus, RoundResult


class GameState:
    def __init__(self) -> None:
        self.game_id: str = uuid.uuid4().hex[:12]
        self.status: GameStatus = GameStatus.WAITING
        self.round: int = 1
        self.history: list[RoundResult] = []
        self.target_image: str = ""
        self.used_targets: list[str] = []
        self._round_start: float = 0.0
        self._timer_task: asyncio.Task | None = None

    @property
    def threshold(self) -> float:
        return min(
            settings.base_threshold + (self.round - 1) * settings.threshold_step,
            settings.max_threshold,
        )

    @property
    def time_remaining(self) -> int:
        if self._round_start == 0:
            return settings.round_time_seconds
        elapsed = time.time() - self._round_start
        return max(0, settings.round_time_seconds - int(elapsed))

    def start_round(self, target_image: str) -> None:
        self.target_image = target_image
        self.used_targets.append(target_image)
        self.status = GameStatus.PLAYING
        self._round_start = time.time()

    def game_over(self) -> None:
        self.status = GameStatus.GAME_OVER
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()


# Active games registry
_games: dict[str, GameState] = {}


def create_game() -> GameState:
    game = GameState()
    _games[game.game_id] = game
    return game


def get_game(game_id: str) -> GameState | None:
    return _games.get(game_id)


def remove_game(game_id: str) -> None:
    _games.pop(game_id, None)

"""Persists game rounds to disk: JSON metadata + image files."""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path

from backend.config import settings


def _game_dir(game_id: str, started: datetime) -> Path:
    ts = started.strftime("%Y-%m-%d_%H-%M-%S")
    return settings.history_dir / f"{ts}_{game_id}"


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _save_image(data_b64: str, path: Path) -> None:
    """Decode base64 image and write to file."""
    if not data_b64:
        return
    path.write_bytes(base64.b64decode(data_b64))


def save_round_single(
    game_id: str,
    started: datetime,
    round_num: int,
    target_image_name: str,
    prompt: str,
    score: float,
    threshold: float,
    passed: bool,
    generated_b64: str,
    reason: str = "",
    generation_time: float | None = None,
    scoring_time: float | None = None,
    error: str | None = None,
) -> None:
    """Save a single-player round result."""
    game = _ensure_dir(_game_dir(game_id, started))
    rdir = _ensure_dir(game / f"round_{round_num}")

    # Save generated image
    _save_image(generated_b64, rdir / "generated.webp")

    # Save metadata
    result: dict = {
        "round": round_num,
        "mode": "single",
        "game_id": game_id,
        "target_image": target_image_name,
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "score": score,
        "threshold": threshold,
        "passed": passed,
        "reason": reason,
        "image_backend": settings.image_backend,
        "image_model": settings.gemini_model if settings.image_backend == "gemini" else settings.flux_model,
        "similarity_backend": settings.similarity_backend,
        "similarity_model": settings.similarity_gemini_model if settings.similarity_backend == "gemini" else settings.clip_model,
    }
    if settings.prompt_prefix:
        result["prompt_prefix"] = settings.prompt_prefix
    if generation_time is not None:
        result["generation_time_seconds"] = round(generation_time, 2)
    if scoring_time is not None:
        result["scoring_time_seconds"] = round(scoring_time, 2)
    if error:
        result["error"] = error
    (rdir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Update game.json
    _update_game_json(game, game_id, "single", started)


def save_round_multi(
    game_id: str,
    started: datetime,
    round_num: int,
    target_image_name: str,
    player1: dict,
    player2: dict,
    winner: int,
) -> None:
    """Save a multiplayer round result.

    player1/player2 dicts contain: prompt, score, generated_image (base64),
    optionally generation_time, scoring_time
    """
    game = _ensure_dir(_game_dir(game_id, started))
    rdir = _ensure_dir(game / f"round_{round_num}")

    # Save generated images
    _save_image(player1.get("generated_image", ""), rdir / "player1.webp")
    _save_image(player2.get("generated_image", ""), rdir / "player2.webp")

    def _player_entry(num: int, data: dict) -> dict:
        entry: dict = {
            "player": num,
            "prompt": data.get("prompt", ""),
            "score": data.get("score", 0),
            "reason": data.get("reason", ""),
        }
        if data.get("generation_time") is not None:
            entry["generation_time_seconds"] = round(data["generation_time"], 2)
        if data.get("scoring_time") is not None:
            entry["scoring_time_seconds"] = round(data["scoring_time"], 2)
        if data.get("error"):
            entry["error"] = data["error"]
        return entry

    # Save metadata
    result: dict = {
        "round": round_num,
        "mode": "multi",
        "game_id": game_id,
        "target_image": target_image_name,
        "timestamp": datetime.now().isoformat(),
        "players": [
            _player_entry(1, player1),
            _player_entry(2, player2),
        ],
        "winner": winner,
        "image_backend": settings.image_backend,
        "image_model": settings.gemini_model if settings.image_backend == "gemini" else settings.flux_model,
        "similarity_backend": settings.similarity_backend,
        "similarity_model": settings.similarity_gemini_model if settings.similarity_backend == "gemini" else settings.clip_model,
    }
    if settings.prompt_prefix:
        result["prompt_prefix"] = settings.prompt_prefix
    (rdir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    # Update game.json
    _update_game_json(game, game_id, "multi", started)


def save_game_end(
    game_id: str,
    started: datetime,
    mode: str,
    total_rounds: int,
    final_score: dict | None = None,
) -> None:
    """Write final game summary."""
    game = _game_dir(game_id, started)
    if not game.exists():
        return

    summary = {
        "game_id": game_id,
        "mode": mode,
        "started": started.isoformat(),
        "ended": datetime.now().isoformat(),
        "rounds": total_rounds,
    }
    if final_score:
        summary["final_score"] = final_score

    (game / "game.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))


def _update_game_json(game_dir: Path, game_id: str, mode: str, started: datetime) -> None:
    """Keep game.json up to date after each round."""
    gj = game_dir / "game.json"
    if gj.exists():
        data = json.loads(gj.read_text())
    else:
        data = {
            "game_id": game_id,
            "mode": mode,
            "started": started.isoformat(),
        }

    # Count round dirs
    rounds = sorted(game_dir.glob("round_*"))
    data["rounds"] = len(rounds)
    data["last_updated"] = datetime.now().isoformat()

    gj.write_text(json.dumps(data, indent=2, ensure_ascii=False))

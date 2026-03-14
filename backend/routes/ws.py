import asyncio
import json
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from PIL import Image

from backend.config import settings
from backend.game_state import get_game, GameState
from backend.models import GameStatus, RoundResult
from backend.services.image_generator import generate_image, image_to_base64
from backend.services.similarity import compute_similarity
from backend.services.target_images import pick_random_target, target_image_path

router = APIRouter()


async def send_json(ws: WebSocket, msg_type: str, data: dict | None = None) -> None:
    await ws.send_json({"type": msg_type, "data": data or {}})


@router.websocket("/ws/{game_id}")
async def game_websocket(ws: WebSocket, game_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004, reason="Game not found")
        return

    await ws.accept()

    timer_task: asyncio.Task | None = None

    async def run_timer():
        try:
            while game.time_remaining > 0 and game.status == GameStatus.PLAYING:
                await send_json(ws, "timer_tick", {"remaining": game.time_remaining})
                await asyncio.sleep(1)
            if game.status == GameStatus.PLAYING:
                game.game_over()
                await send_json(ws, "time_up", {})
                await send_json(ws, "game_over", {
                    "round": game.round,
                    "history": [r.model_dump() for r in game.history],
                })
        except (WebSocketDisconnect, Exception):
            pass

    try:
        # Start timer
        timer_task = asyncio.create_task(run_timer())
        game._timer_task = timer_task

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "submit_prompt":
                if game.status != GameStatus.PLAYING:
                    await send_json(ws, "error", {"message": "Not in playing state"})
                    continue

                prompt = msg.get("data", {}).get("prompt", "").strip()
                if not prompt:
                    await send_json(ws, "error", {"message": "Empty prompt"})
                    continue

                # Cancel timer during generation
                if timer_task and not timer_task.done():
                    timer_task.cancel()

                game.status = GameStatus.GENERATING

                # Progress callback via websocket
                async def send_progress(step: int, total: int):
                    await send_json(ws, "generation_progress", {
                        "step": step, "total": total
                    })

                # We need a sync callback that schedules the async send
                loop = asyncio.get_running_loop()

                def step_callback(step: int, total: int):
                    asyncio.run_coroutine_threadsafe(
                        send_progress(step, total), loop
                    )

                # Generate image
                generated = await generate_image(prompt, step_callback=step_callback)
                gen_b64 = image_to_base64(generated)

                await send_json(ws, "generation_complete", {
                    "image": gen_b64,
                })

                # Compute similarity
                target_img = Image.open(target_image_path(game.target_image)).convert("RGB")
                score = compute_similarity(target_img, generated)
                passed = score >= game.threshold

                round_result = RoundResult(
                    round=game.round,
                    prompt=prompt,
                    score=round(score, 1),
                    threshold=game.threshold,
                    passed=passed,
                    generated_image=gen_b64,
                    target_image=game.target_image,
                )
                game.history.append(round_result)

                await send_json(ws, "score_result", {
                    "score": round(score, 1),
                    "threshold": game.threshold,
                    "passed": passed,
                    "round": game.round,
                    "generated_image": gen_b64,
                })

                game.status = GameStatus.RESULT

                if not passed:
                    game.game_over()

            elif msg_type == "next_round":
                if game.status != GameStatus.RESULT:
                    await send_json(ws, "error", {"message": "Not in result state"})
                    continue

                game.round += 1
                target = pick_random_target(exclude=game.used_targets)
                game.start_round(target)

                await send_json(ws, "round_start", {
                    "round": game.round,
                    "target_image": target,
                    "threshold": game.threshold,
                    "time_seconds": settings.round_time_seconds,
                })

                # Restart timer
                timer_task = asyncio.create_task(run_timer())
                game._timer_task = timer_task

    except WebSocketDisconnect:
        pass
    finally:
        if timer_task and not timer_task.done():
            timer_task.cancel()

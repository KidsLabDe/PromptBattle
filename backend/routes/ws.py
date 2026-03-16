import asyncio
import json
import time
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from PIL import Image

from backend.config import settings
from backend.game_state import get_game, create_game, GameState
from backend.models import GameMode, GameStatus, RoundResult
from backend.services.history import save_round_single, save_round_multi, save_game_end
from backend.services.image_generator import generate_image, image_to_base64
from backend.services.similarity import compute_similarity
from backend.services.target_images import pick_random_target, target_image_path

router = APIRouter()

# Connection registry for multiplayer: game_id -> {role: WebSocket}
_connections: dict[str, dict[str, WebSocket]] = {}


async def send_json(ws: WebSocket, msg_type: str, data: dict | None = None) -> None:
    try:
        await ws.send_json({"type": msg_type, "data": data or {}})
    except Exception:
        pass


async def broadcast(game_id: str, msg_type: str, data: dict, targets: list[str] | None = None) -> None:
    """Send message to specific roles or all connections for a game."""
    conns = _connections.get(game_id, {})
    roles = targets or list(conns.keys())
    for role in roles:
        ws = conns.get(role)
        if ws:
            await send_json(ws, msg_type, data)


def register_connection(game_id: str, role: str, ws: WebSocket) -> None:
    if game_id not in _connections:
        _connections[game_id] = {}
    _connections[game_id][role] = ws


def unregister_connection(game_id: str, role: str) -> None:
    conns = _connections.get(game_id, {})
    conns.pop(role, None)
    if not conns:
        _connections.pop(game_id, None)


# ── Single-player WebSocket ──────────────────────────────────

@router.websocket("/ws/{game_id}")
async def game_websocket(ws: WebSocket, game_id: str):
    game = get_game(game_id)
    if not game:
        await ws.close(code=4004, reason="Game not found")
        return

    await ws.accept()
    register_connection(game_id, "main", ws)

    timer_task: asyncio.Task | None = None

    async def run_timer():
        try:
            while game.time_remaining > 0 and game.status == GameStatus.PLAYING:
                await broadcast(game_id, "timer_tick", {"remaining": game.time_remaining})
                await asyncio.sleep(1)
            if game.status == GameStatus.PLAYING:
                if game.num_players > 0:
                    # Phone-controlled (single or multi via lobby)
                    await _handle_multi_time_up(game)
                else:
                    # Traditional single player (keyboard on main screen)
                    game.game_over()
                    await send_json(ws, "time_up", {})
                    await send_json(ws, "game_over", {
                        "round": game.round,
                        "history": [r.model_dump() for r in game.history],
                    })
        except (WebSocketDisconnect, Exception):
            pass

    try:
        if game.mode == GameMode.SINGLE:
            # Traditional single player — start timer immediately
            timer_task = asyncio.create_task(run_timer())
            game._timer_task = timer_task

        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if game.mode == GameMode.SINGLE and game.num_players == 0:
                # Traditional single player (no phone)
                await _handle_single_player_msg(ws, game, msg_type, msg, timer_task)
            else:
                # Multiplayer or single-via-phone (lobby flow)
                await _handle_main_screen_msg(ws, game, msg_type, msg, timer_task)

    except WebSocketDisconnect:
        pass
    finally:
        if timer_task and not timer_task.done():
            timer_task.cancel()
        unregister_connection(game_id, "main")


async def _handle_single_player_msg(
    ws: WebSocket, game: GameState, msg_type: str, msg: dict,
    timer_task: asyncio.Task | None
) -> None:
    if msg_type == "submit_prompt":
        if game.status != GameStatus.PLAYING:
            await send_json(ws, "error", {"message": "Not in playing state"})
            return

        prompt = msg.get("data", {}).get("prompt", "").strip()
        if not prompt:
            await send_json(ws, "error", {"message": "Empty prompt"})
            return

        if timer_task and not timer_task.done():
            timer_task.cancel()

        game.status = GameStatus.GENERATING

        loop = asyncio.get_running_loop()

        def step_callback(step: int, total: int):
            asyncio.run_coroutine_threadsafe(
                send_json(ws, "generation_progress", {"step": step, "total": total}),
                loop,
            )

        generated = await generate_image(prompt, step_callback=step_callback)
        gen_b64 = image_to_base64(generated)

        await send_json(ws, "generation_complete", {"image": gen_b64})

        target_img = Image.open(target_image_path(game.target_image)).convert("RGB")
        score = await compute_similarity(target_img, generated)
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

        # Save round to disk
        save_round_single(
            game_id=game.game_id,
            started=game.started,
            round_num=game.round,
            target_image_name=game.target_image,
            prompt=prompt,
            score=round(score, 1),
            threshold=game.threshold,
            passed=passed,
            generated_b64=gen_b64,
        )

        if not passed:
            game.game_over()
            save_game_end(
                game_id=game.game_id,
                started=game.started,
                mode="single",
                total_rounds=game.round,
            )

    elif msg_type == "next_round":
        if game.status != GameStatus.RESULT:
            await send_json(ws, "error", {"message": "Not in result state"})
            return

        game.round += 1
        target = pick_random_target(exclude=game.used_targets)
        game.start_round(target)

        await send_json(ws, "round_start", {
            "round": game.round,
            "target_image": target,
            "threshold": game.threshold,
            "time_seconds": settings.round_time_seconds,
        })


# ── Multiplayer: main screen messages ────────────────────────

async def _handle_main_screen_msg(
    ws: WebSocket, game: GameState, msg_type: str, msg: dict,
    timer_task: asyncio.Task | None,
) -> None:
    if msg_type == "start_game":
        # Host clicked start - determine mode based on connected players
        conns = _connections.get(game.game_id, {})
        num_players = sum(1 for k in conns if k.startswith("player"))
        if num_players == 0:
            await send_json(ws, "error", {"message": "Kein Spieler verbunden"})
            return

        game.num_players = num_players
        await broadcast(game.game_id, "game_mode_set", {
            "mode": "single" if num_players == 1 else "multi",
            "num_players": num_players,
        })

        # Start the round with fresh timer
        game.start_round(game.target_image)
        # Remove duplicate from used_targets since start_round adds it again
        if game.used_targets.count(game.target_image) > 1:
            game.used_targets.pop()

        await broadcast(game.game_id, "round_start", {
            "round": game.round,
            "target_image": game.target_image,
            "threshold": game.threshold,
            "time_seconds": settings.round_time_seconds,
        })

        # Start timer
        async def lobby_timer():
            try:
                while game.time_remaining > 0 and game.status == GameStatus.PLAYING:
                    await broadcast(game.game_id, "timer_tick", {"remaining": game.time_remaining})
                    await asyncio.sleep(1)
                if game.status == GameStatus.PLAYING:
                    await _handle_multi_time_up(game)
            except Exception:
                pass

        new_timer = asyncio.create_task(lobby_timer())
        game._timer_task = new_timer

    elif msg_type == "next_round":
        if game.status != GameStatus.RESULT:
            return
        await _start_next_multi_round(game)

    elif msg_type == "restart_game":
        await _auto_restart_multi(game)


# ── Multiplayer: player WebSocket ────────────────────────────

@router.websocket("/ws/{game_id}/player/{token}")
async def player_websocket(ws: WebSocket, game_id: str, token: str):
    await ws.accept()

    game = get_game(game_id)
    if not game:
        await ws.close(code=4004, reason="Game not found")
        return

    # Try join_token first (dynamic assignment)
    player = None
    if token == game.join_token:
        # Check if a previously assigned player has disconnected — reconnect them
        conns = _connections.get(game_id, {})
        for pnum in sorted(game.player_tokens.keys()):
            role_key = f"player{pnum}"
            if role_key not in conns:
                # This player slot exists but has no active connection — reconnect
                player = pnum
                break
        if player is None:
            # No disconnected player — assign a new one
            player = game.assign_player(token)
    else:
        # Try existing player token (reconnect)
        player = game.get_player_by_token(token)

    if player is None:
        await ws.close(code=4003, reason="Invalid token or game full")
        return
    role = f"player{player}"
    register_connection(game_id, role, ws)

    # Notify player
    await send_json(ws, "connected", {
        "player": player,
        "round": game.round,
        "time_remaining": game.time_remaining,
    })

    # Notify main screen
    await broadcast(game_id, "player_connected", {"player": player}, targets=["main"])

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "typing":
                # Forward live typing to main screen for audience
                text = msg.get("data", {}).get("text", "")
                await broadcast(game_id, "player_typing", {
                    "player": player, "text": text,
                }, targets=["main"])

            elif msg_type == "submit_prompt":
                if game.status != GameStatus.PLAYING:
                    await send_json(ws, "error", {"message": "Not in playing state"})
                    continue

                prompt = msg.get("data", {}).get("prompt", "").strip()
                if not prompt:
                    await send_json(ws, "error", {"message": "Empty prompt"})
                    continue

                if player in game.prompts:
                    await send_json(ws, "error", {"message": "Already submitted"})
                    continue

                both_ready = game.submit_player_prompt(player, prompt)

                await send_json(ws, "prompt_accepted", {"player": player})
                await broadcast(game_id, "prompt_submitted", {
                    "player": player, "prompt": prompt,
                }, targets=["main"])

                if both_ready:
                    if game._timer_task and not game._timer_task.done():
                        game._timer_task.cancel()
                    asyncio.create_task(_run_multi_generation(game))

    except WebSocketDisconnect:
        pass
    finally:
        unregister_connection(game_id, role)
        await broadcast(game_id, "player_disconnected", {"player": player}, targets=["main"])


# ── Multiplayer: generation + scoring pipeline ───────────────

async def _run_multi_generation(game: GameState) -> None:
    """Generate images for players, score them, broadcast results."""
    if game._generation_running:
        return
    game._generation_running = True
    game.status = GameStatus.GENERATING
    game_id = game.game_id
    loop = asyncio.get_running_loop()
    try:
        await _run_multi_generation_inner(game, game_id, loop)
    except Exception as e:
        import traceback
        print(f"ERROR in _run_multi_generation: {e}")
        traceback.print_exc()
        await broadcast(game_id, "error", {"message": f"Generation error: {e}"})
        game.game_over()
        await broadcast(game_id, "game_over", {
            "round": game.round,
            "history": [r.model_dump() for r in game.history],
        })
    finally:
        game._generation_running = False


def _error_placeholder_b64() -> str:
    """Generate a small black placeholder image as base64."""
    img = Image.new("RGB", (64, 64), (0, 0, 0))
    return image_to_base64(img)


async def _generate_for_player(
    player_num: int, prompt: str, target_img,
    game_id: str, loop,
) -> dict | None:
    """Generate image + compute score for one player. Returns result dict or None on error."""
    try:
        await broadcast(game_id, "generation_start", {"player": player_num}, targets=["main", f"player{player_num}"])

        def make_step_cb(pnum: int):
            def step_callback(step: int, total: int):
                asyncio.run_coroutine_threadsafe(
                    broadcast(game_id, "generation_progress", {
                        "player": pnum, "step": step, "total": total,
                    }, targets=["main"]),
                    loop,
                )
            return step_callback

        generated = await generate_image(prompt, step_callback=make_step_cb(player_num))
        gen_b64 = image_to_base64(generated)

        print(f"[GEN {datetime.now().strftime('%H:%M:%S')}] Player {player_num} image generated, broadcasting...")
        await broadcast(game_id, "generation_complete", {
            "player": player_num, "image": gen_b64,
        }, targets=["main"])

        print(f"[GEN {datetime.now().strftime('%H:%M:%S')}] Computing similarity for player {player_num}...")
        score = await compute_similarity(target_img, generated)
        return {
            "prompt": prompt,
            "score": round(score, 1),
            "generated_image": gen_b64,
        }
    except Exception as e:
        print(f"ERROR generating for player {player_num}: {e}")
        return None


async def _run_multi_generation_inner(game: GameState, game_id: str, loop) -> None:
    """Inner generation logic."""
    print(f"[GEN {datetime.now().strftime('%H:%M:%S')}] Starting generation for game {game_id}, players: {game.num_players}, prompts: {game.prompts}")

    target_img = Image.open(target_image_path(game.target_image)).convert("RGB")

    player_nums = list(range(1, game.num_players + 1))

    # Generate images for all players in parallel
    tasks = [
        _generate_for_player(pnum, game.prompts.get(pnum, ""), target_img, game_id, loop)
        for pnum in player_nums
    ]
    raw_results = await asyncio.gather(*tasks)

    # Build results dict with fallback for failures
    results: dict[int, dict] = {}
    for i, player_num in enumerate(player_nums):
        if raw_results[i] is not None:
            results[player_num] = raw_results[i]
        else:
            placeholder = _error_placeholder_b64()
            results[player_num] = {
                "prompt": game.prompts.get(player_num, ""),
                "score": 0.0,
                "generated_image": placeholder,
            }
            await broadcast(game_id, "generation_complete", {
                "player": player_num, "image": placeholder,
            }, targets=["main"])

    if game.num_players == 1:
        # Single player via phone — score against threshold
        score = results[1]["score"]
        passed = score >= game.threshold

        round_result = RoundResult(
            round=game.round,
            prompt=results[1]["prompt"],
            score=score,
            threshold=game.threshold,
            passed=passed,
            generated_image=results[1]["generated_image"],
            target_image=game.target_image,
        )
        game.history.append(round_result)

        print(f"[GEN {datetime.now().strftime('%H:%M:%S')}] Single player score: {score}%, threshold: {game.threshold}%, passed: {passed}")
        await broadcast(game_id, "score_result", {
            "score": score,
            "threshold": game.threshold,
            "passed": passed,
            "round": game.round,
            "generated_image": results[1]["generated_image"],
        }, targets=["main"])

        await broadcast(game_id, "player_result", {
            "player": 1,
            "score": score,
            "threshold": game.threshold,
            "passed": passed,
            "round": game.round,
        }, targets=["player1"])

        game.status = GameStatus.RESULT

        save_round_single(
            game_id=game.game_id,
            started=game.started,
            round_num=game.round,
            target_image_name=game.target_image,
            prompt=results[1]["prompt"],
            score=score,
            threshold=game.threshold,
            passed=passed,
            generated_b64=results[1]["generated_image"],
        )

        if not passed:
            game.game_over()
            await broadcast(game_id, "game_over", {
                "round": game.round,
                "history": [r.model_dump() for r in game.history],
            })
            save_game_end(
                game_id=game.game_id,
                started=game.started,
                mode="single",
                total_rounds=game.round,
            )
        else:
            asyncio.create_task(_auto_advance_after_result(game))
    else:
        # Multiplayer — compare scores
        s1 = results[1]["score"]
        s2 = results[2]["score"]
        if s1 > s2:
            winner = 1
            game.player1_wins += 1
        elif s2 > s1:
            winner = 2
            game.player2_wins += 1
        else:
            winner = 0

        result_data = {
            "player1": {"player": 1, **results[1]},
            "player2": {"player": 2, **results[2]},
            "winner": winner,
            "round": game.round,
            "player1_wins": game.player1_wins,
            "player2_wins": game.player2_wins,
        }

        await broadcast(game_id, "multi_score_result", result_data, targets=["main"])

        for pnum in [1, 2]:
            await broadcast(game_id, "player_result", {
                "player": pnum,
                "score": results[pnum]["score"],
                "opponent_score": results[3 - pnum]["score"],
                "winner": winner,
                "round": game.round,
            }, targets=[f"player{pnum}"])

        game.status = GameStatus.RESULT

        save_round_multi(
            game_id=game.game_id,
            started=game.started,
            round_num=game.round,
            target_image_name=game.target_image,
            player1=results[1],
            player2=results[2],
            winner=winner,
        )

        asyncio.create_task(_auto_advance_after_result(game))


async def _auto_advance_after_result(game: GameState) -> None:
    """Auto-advance to next round after showing results."""
    delay = settings.multi_result_display_seconds

    # Countdown broadcast so frontend can show it
    for i in range(delay, 0, -1):
        await broadcast(game.game_id, "auto_countdown", {"seconds": i})
        await asyncio.sleep(1)
        if game.status != GameStatus.RESULT:
            return  # manually advanced or game ended

    if game.status == GameStatus.RESULT:
        await _start_next_multi_round(game)


async def _start_next_multi_round(game: GameState) -> None:
    """Start a new round in the current multiplayer game."""
    game.round += 1
    target = pick_random_target(exclude=game.used_targets)
    game.start_round(target)

    data = {
        "round": game.round,
        "target_image": target,
        "threshold": game.threshold,
        "time_seconds": settings.round_time_seconds,
    }
    await broadcast(game.game_id, "round_start", data)

    # Restart timer
    async def run_timer():
        try:
            while game.time_remaining > 0 and game.status == GameStatus.PLAYING:
                await broadcast(game.game_id, "timer_tick", {"remaining": game.time_remaining})
                await asyncio.sleep(1)
            if game.status == GameStatus.PLAYING:
                await _handle_multi_time_up(game)
        except Exception:
            pass

    timer_task = asyncio.create_task(run_timer())
    game._timer_task = timer_task


async def _handle_multi_time_up(game: GameState) -> None:
    """Handle time running out."""
    game_id = game.game_id

    if game.num_players == 1:
        # Single player via phone — time up = game over
        if len(game.prompts) == 0:
            game.game_over()
            await broadcast(game_id, "time_up", {})
            await broadcast(game_id, "game_over", {
                "round": game.round,
                "history": [r.model_dump() for r in game.history],
            })
        # If already submitted, generation is running
        return

    if len(game.prompts) == 1:
        # One player submitted — give empty prompt to other, run generation
        submitted_player = list(game.prompts.keys())[0]
        other_player = 3 - submitted_player
        game.prompts[other_player] = "(kein Prompt eingereicht)"

        await broadcast(game_id, "time_up", {})
        await _run_multi_generation(game)
    elif len(game.prompts) == 0:
        # Nobody submitted — auto-restart after delay
        await broadcast(game_id, "time_up", {})
        await broadcast(game_id, "auto_restart", {
            "seconds": settings.multi_restart_delay_seconds,
            "player1_wins": game.player1_wins,
            "player2_wins": game.player2_wins,
        })
        await asyncio.sleep(settings.multi_restart_delay_seconds)
        await _auto_restart_multi(game)


async def _auto_restart_multi(game: GameState) -> None:
    """Create a fresh multiplayer game and redirect all clients."""
    old_game_id = game.game_id
    game.game_over()

    # Save game summary
    save_game_end(
        game_id=game.game_id,
        started=game.started,
        mode="multi",
        total_rounds=game.round,
        final_score={"player1": game.player1_wins, "player2": game.player2_wins},
    )

    new_game = create_game(mode=GameMode.MULTI)
    target = pick_random_target()
    new_game.start_round(target)

    await broadcast(old_game_id, "new_game", {
        "game_id": new_game.game_id,
        "target_image": target,
        "round": new_game.round,
        "threshold": new_game.threshold,
        "time_seconds": new_game.time_remaining,
        "join_token": new_game.join_token,
    })

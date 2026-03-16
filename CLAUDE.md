# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Backend
uv sync                          # Install Python dependencies
uv run run.py                    # Start backend (Uvicorn, default port 8000)

# Frontend
cd frontend && npm install       # Install Node dependencies
cd frontend && npm run build     # Build static site to frontend/build/
cd frontend && npm run dev       # Dev server on :5173 (proxies /api + /ws to :8000)
cd frontend && npm run check     # Svelte + TypeScript checking

# Production: just `uv run run.py` — FastAPI serves the built frontend from frontend/build/
```

## Architecture

**Prompt Battle** is a real-time AI image generation game. Players submit text prompts, the app generates images via AI, and scores them against a target image.

### Backend (Python, FastAPI)

- `run.py` — Entry point, starts Uvicorn
- `backend/main.py` — FastAPI app, mounts routes and static files, loads models at startup
- `backend/config.py` — All settings via pydantic-settings with `PB_` env prefix (from `.env`)
- `backend/game_state.py` — `GameState` class with round/timer/prompt state, in-memory registry `_games`
- `backend/models.py` — Enums (`GameStatus`, `GameMode`) and Pydantic models (`RoundResult`)
- `backend/routes/game.py` — REST: `POST /api/game/start`, `GET /api/images/target/{name}`
- `backend/routes/ws.py` — All WebSocket logic: connection registry, game flow, generation pipeline, timer management. This is the largest and most complex file.
- `backend/services/image_generator.py` — Image generation: local (diffusers/FLUX) or Gemini API. Async wrapper via `run_in_executor`.
- `backend/services/similarity.py` — Scoring: local CLIP cosine similarity or Gemini vision API
- `backend/services/history.py` — Saves rounds/games to `generated_history/` on disk
- `backend/services/target_images.py` — Random target image picker from `target_images/`

### Frontend (SvelteKit 2, Svelte 5 runes, TypeScript, Tailwind CSS 4)

- `frontend/src/routes/+page.svelte` — Main orchestrator: all game state transitions, WS message handling, UI phase management (lobby → playing → generating → comparing → result → gameover)
- `frontend/src/routes/play/[gameId]/[token]/+page.svelte` — Phone player view (prompt input, result display)
- `frontend/src/lib/stores/gameStore.ts` — All game state as Svelte writable stores
- `frontend/src/lib/websocket.ts` — WebSocket client with auto-reconnect
- `frontend/src/lib/components/` — UI components (MultiplayerGame, MultiplayerResult, QRLobby, Timer, etc.)
- Static adapter builds to `frontend/build/` (SPA fallback to index.html)

### Communication

All real-time communication uses WebSocket JSON messages: `{"type": "...", "data": {...}}`.

Two WS endpoints:
- `/ws/{gameId}` — Main display screen (role: "main")
- `/ws/{gameId}/player/{token}` — Phone player connections (role: "player1"/"player2")

Connection registry in `ws.py`: `_connections: dict[game_id, dict[role, WebSocket]]`

### Game Flow (Multiplayer)

1. **Lobby**: Main screen creates game, shows QR code. Players scan → WS connect → `player_connected`
2. **Start**: 2 players connected → `start_game` → `game_mode_set` + `round_start` broadcast
3. **Playing**: 60s timer, players type (`typing` → `player_typing`) and submit (`submit_prompt` → `prompt_accepted`)
4. **Generation**: Both prompts in → `_run_multi_generation()` runs parallel `asyncio.gather` → `generation_start/complete` per player
5. **Scoring**: `compute_similarity()` per player → `multi_score_result` broadcast with winner
6. **Result**: Frontend shows compare animation (4s) then score reveal (2.5s)
7. **Auto-advance**: Countdown → next round with new target image

### Image Generation Backends

Configured via `PB_IMAGE_BACKEND`:
- `local` — diffusers pipeline (FLUX.1-schnell default), needs GPU
- `gemini` — Google Gemini API (`PB_GEMINI_API_KEY` required)

### Similarity Scoring Backends

Configured via `PB_SIMILARITY_BACKEND`:
- `clip` — Local CLIP model, cosine similarity scaled to 0-100%
- `gemini` — Gemini vision API scores image pair with German prompt

## Key Conventions

- All config uses `PB_` prefixed env vars (see `backend/config.py` for all options)
- Frontend uses Svelte 5 runes (`$state`, `$derived`, `$effect`) — not legacy `$:` syntax
- UI language is German throughout
- Dark theme with neon color palette (green, pink, blue, yellow)
- Custom pixel font: Pixelify Sans
- No automated tests exist

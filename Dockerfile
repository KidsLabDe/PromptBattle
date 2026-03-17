# ── Stage 1: Frontend bauen ──────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python Backend ─────────────────────────────
FROM python:3.12-slim AS production

# System-Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv installieren
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Python-Dependencies installieren
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# App-Code kopieren
COPY backend/ ./backend/
COPY run.py ./
COPY target_images/ ./target_images/

# Frontend-Build aus Stage 1 kopieren
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Verzeichnisse für generierte Daten
RUN mkdir -p generated_history backend/generated

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/api/config || exit 1

CMD ["uv", "run", "python", "run.py"]

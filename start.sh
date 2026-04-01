#!/usr/bin/env bash
cd "$(dirname "$0")"

# PyTorch cu118 für GTX 1080 (sm_61) sicherstellen
EXPECTED="2.7.1+cu118"
ACTUAL=$(uv run python -c "import torch; print(torch.__version__)" 2>/dev/null)
if [ "$ACTUAL" != "$EXPECTED" ]; then
    echo "PyTorch $ACTUAL → installiere $EXPECTED (cu118 für GTX 1080)..."
    uv pip install torch==2.7.1+cu118 --index-url https://download.pytorch.org/whl/cu118
fi

uv run run.py

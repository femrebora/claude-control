#!/usr/bin/env bash
# Launch claude-control bound to loopback only.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

if [[ "$HOST" != "127.0.0.1" && "$HOST" != "localhost" ]]; then
  echo "WARNING: binding to $HOST. claude-control has no auth. Make sure your firewall blocks $PORT from untrusted networks."
fi

# Use venv python if available, otherwise fall back to system python
PYTHON="$PROJECT_DIR/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

exec "$PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload

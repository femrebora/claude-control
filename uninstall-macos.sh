#!/usr/bin/env bash
# Removes the macOS .app bundle. Leaves project files alone.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/Applications/Claude Control.app"

if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/launcher.py" --stop || true
fi

green() { printf '\033[32m%s\033[0m\n' "$1"; }

rm -rf "$APP_DIR"

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}/claude-control"

green "✓ App bundle removed."
echo "  To remove project files:  rm -rf $PROJECT_DIR"
echo "  To remove runtime files:  rm -rf $RUNTIME_DIR"

#!/usr/bin/env bash
# Installs claude-control as a clickable Ubuntu application.
# - Creates a Python venv inside the project
# - Installs dependencies
# - Places a .desktop entry in ~/.local/share/applications/
# - Registers the icon
#
# After this runs, "Claude Control" appears in your Activities / app grid.
# Click it to launch — no terminal commands needed afterwards.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_FILE="$APPS_DIR/claude-control.desktop"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }

bold "▸ Installing claude-control as a desktop application"
echo "  Project dir: $PROJECT_DIR"
echo

# 1. Python check
if ! command -v python3 >/dev/null; then
  echo "ERROR: python3 not found. Install with: sudo apt install python3 python3-venv" >&2
  exit 1
fi

# 2. venv
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  bold "▸ Creating Python venv"
  python3 -m venv "$PROJECT_DIR/.venv"
fi

# 3. deps
bold "▸ Installing Python dependencies"
"$PROJECT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install --quiet -r "$PROJECT_DIR/requirements.txt"

# Optional: pywebview for native window mode (silently skip if it fails)
if "$PROJECT_DIR/.venv/bin/pip" install --quiet pywebview 2>/dev/null; then
  green "  ✓ pywebview installed (native window mode available)"
else
  yellow "  ⚠ pywebview not installed (native window mode unavailable; falling back to browser)"
fi

# 4. .desktop file (substitute __INSTALL_PATH__)
bold "▸ Registering desktop entry"
mkdir -p "$APPS_DIR"
sed "s|__INSTALL_PATH__|$PROJECT_DIR|g" \
  "$PROJECT_DIR/assets/claude-control.desktop.in" > "$DESKTOP_FILE"
# GNOME trusts .desktop files in this directory; executable bit is not needed
if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate "$DESKTOP_FILE" 2>/dev/null || true
fi

# 5. icons
mkdir -p "$ICONS_DIR"
cp "$PROJECT_DIR/assets/icon.png" "$ICONS_DIR/claude-control.png"
cp "$PROJECT_DIR/assets/claude-control-icon.svg" "$ICONS_DIR/claude-control.svg"

# 6. refresh app database (best-effort; silently OK if not available)
if command -v update-desktop-database >/dev/null; then
  update-desktop-database "$APPS_DIR" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null; then
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo
green "✓ Installed successfully."
echo
bold "Getting started"
echo "  1. Open the Activities overview (Super key) and search 'Claude Control'."
echo "  2. Click the icon to launch — the dashboard opens in your browser."
echo "  3. Right-click the icon while running and select 'Pin to Dash' to keep it handy."
echo
bold "Commands"
echo "  Uninstall:      bash $PROJECT_DIR/uninstall.sh"
echo "  Launch via CLI: $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/launcher.py"
echo "  Stop server:    $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/launcher.py --stop"
echo "  Run in terminal: cd $PROJECT_DIR && ./run.sh"

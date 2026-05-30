#!/usr/bin/env bash
# Installs claude-control as a clickable macOS application.
# - Creates a Python venv inside the project
# - Installs dependencies
# - Builds a minimal .app bundle in ~/Applications/
# - Registers the icon
#
# After this runs, "Claude Control" appears in Launchpad / Spotlight.
# Click it to launch — no terminal commands needed afterwards.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Claude Control"
APP_DIR="$HOME/Applications/${APP_NAME}.app"
CONTENTS="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS/MacOS"
RESOURCES_DIR="$CONTENTS/Resources"

bold() { printf '\033[1m%s\033[0m\n' "$1"; }
green() { printf '\033[32m%s\033[0m\n' "$1"; }
yellow() { printf '\033[33m%s\033[0m\n' "$1"; }

bold "▸ Installing claude-control as a macOS application"
echo "  Project dir: $PROJECT_DIR"
echo "  App bundle:  $APP_DIR"
echo

# 1. Python check
if ! command -v python3 >/dev/null; then
  echo "ERROR: python3 not found. Install with: brew install python" >&2
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

if "$PROJECT_DIR/.venv/bin/pip" install --quiet pywebview pyobjc-framework-WebKit 2>/dev/null; then
  green "  ✓ pywebview installed (native window mode available)"
else
  yellow "  ⚠ pywebview not installed (native window mode unavailable; falling back to browser)"
fi

# 4. Build .app bundle
bold "▸ Building app bundle"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

# Convert PNG → ICNS for the dock icon (best-effort)
if command -v sips >/dev/null && command -v iconutil >/dev/null; then
  ICONSET="$(mktemp -d)/icon.iconset"
  mkdir -p "$ICONSET"
  for size in 16 32 64 128 256 512; do
    sips -z $size $size "$PROJECT_DIR/assets/icon.png" \
      --out "$ICONSET/icon_${size}x${size}.png" >/dev/null 2>&1 || true
  done
  iconutil -c icns "$ICONSET" -o "$RESOURCES_DIR/icon.icns" 2>/dev/null || \
    cp "$PROJECT_DIR/assets/icon.png" "$RESOURCES_DIR/icon.png"
else
  cp "$PROJECT_DIR/assets/icon.png" "$RESOURCES_DIR/icon.png"
fi

# Info.plist
cat > "$CONTENTS/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Claude Control</string>
    <key>CFBundleDisplayName</key>
    <string>Claude Control</string>
    <key>CFBundleIdentifier</key>
    <string>dev.local.claude-control</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>claude-control</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Launcher executable inside the bundle
cat > "$MACOS_DIR/claude-control" <<EOF
#!/usr/bin/env bash
# App-bundle entrypoint. Delegates to launcher.py.
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/launcher.py" "\$@"
EOF
chmod +x "$MACOS_DIR/claude-control"

# Refresh Launch Services so Spotlight finds it immediately
if command -v /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister >/dev/null 2>&1; then
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
    -f "$APP_DIR" 2>/dev/null || true
fi

echo
green "✓ Installed successfully."
echo
bold "Getting started"
echo "  1. Open Launchpad or Spotlight (⌘+Space) and search 'Claude Control'."
echo "  2. Click the icon to launch — the dashboard opens in your browser."
echo "  3. Drag the app from ~/Applications/ to your Dock to keep it handy."
echo
bold "Commands"
echo "  Uninstall:      bash $PROJECT_DIR/uninstall-macos.sh"
echo "  Launch via CLI: $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/launcher.py"
echo "  Stop server:    $PROJECT_DIR/.venv/bin/python $PROJECT_DIR/launcher.py --stop"
echo "  Run in terminal: cd $PROJECT_DIR && ./run.sh"

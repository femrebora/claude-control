#!/usr/bin/env python3
"""
claude-control desktop launcher.

Starts the FastAPI server as a background subprocess on a free port,
waits until it's healthy, opens the dashboard in the user's default browser,
and writes a PID file so re-launching brings the existing instance forward
instead of starting a second copy.

Usage:
    python3 launcher.py            # standard launch
    python3 launcher.py --stop     # stop running instance
    python3 launcher.py --window   # open in pywebview window (if installed)
"""
from __future__ import annotations

import argparse
import os
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _runtime_dir() -> Path:
    """Cross-platform runtime dir for pid/port files."""
    # Linux: prefer XDG_RUNTIME_DIR
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg and Path(xdg).is_dir():
        return Path(xdg) / "claude-control"
    # macOS / fallback
    return Path(tempfile.gettempdir()) / "claude-control"


RUNTIME_DIR = _runtime_dir()
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
PID_FILE = RUNTIME_DIR / "server.pid"
PORT_FILE = RUNTIME_DIR / "server.port"
LOG_FILE = RUNTIME_DIR / "server.log"


def find_free_port(preferred: int = 8765) -> int:
    """Return preferred port if free, else any free port."""
    for port in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("No free port available")


def is_running() -> tuple[bool, int | None, int | None]:
    """Return (running, pid, port)."""
    if not PID_FILE.exists() or not PORT_FILE.exists():
        return False, None, None
    try:
        pid = int(PID_FILE.read_text().strip())
        port = int(PORT_FILE.read_text().strip())
        os.kill(pid, 0)  # signal 0 = check if alive
        return True, pid, port
    except (ValueError, ProcessLookupError, PermissionError):
        return False, None, None


def stop() -> None:
    running, pid, _ = is_running()
    if not running:
        print("claude-control is not running.")
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)
        return
    assert pid is not None
    is_windows = platform.system() == "Windows"
    try:
        # SIGTERM works on Linux/macOS; on Windows fall back to taskkill
        if is_windows:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):  # wait up to 2s
                time.sleep(0.1)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
            else:
                os.kill(pid, signal.SIGKILL)
        print(f"Stopped (pid {pid}).")
    finally:
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)


def wait_healthy(port: int, timeout: float = 10.0) -> bool:
    """Poll the /api/health endpoint until it responds."""
    import urllib.request
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/api/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def start_server() -> int:
    """Start uvicorn in background, return port."""
    port = find_free_port()

    # Prefer the project's venv python if one exists.
    is_windows = platform.system() == "Windows"
    venv_python = (
        ROOT / ".venv" / "Scripts" / "python.exe"
        if is_windows
        else ROOT / ".venv" / "bin" / "python"
    )
    python = str(venv_python) if venv_python.exists() else sys.executable

    log = LOG_FILE.open("a")
    popen_kwargs: dict = {
        "cwd": ROOT,
        "stdout": log,
        "stderr": subprocess.STDOUT,
    }
    if is_windows:
        # CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS detaches on Windows
        popen_kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
        )
    else:
        popen_kwargs["start_new_session"] = True

    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        **popen_kwargs,
    )

    PID_FILE.write_text(str(proc.pid))
    PORT_FILE.write_text(str(port))

    try:
        if not wait_healthy(port):
            raise RuntimeError(f"Server failed to start. See {LOG_FILE}")
    except Exception:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        PID_FILE.unlink(missing_ok=True)
        PORT_FILE.unlink(missing_ok=True)
        raise

    return port


def open_in_browser(port: int) -> None:
    webbrowser.open_new_tab(f"http://127.0.0.1:{port}/")


def open_in_window(port: int) -> None:
    """Open the dashboard in a pywebview native window."""
    try:
        import webview
    except ImportError:
        print("pywebview not installed; falling back to browser.")
        open_in_browser(port)
        return
    webview.create_window("claude-control", f"http://127.0.0.1:{port}/", width=1200, height=800)
    webview.start()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stop", action="store_true", help="Stop the running instance")
    parser.add_argument("--window", action="store_true", help="Open in a native window (requires pywebview)")
    args = parser.parse_args()

    if args.stop:
        stop()
        return 0

    running, _, port = is_running()
    if running:
        assert port is not None
        print(f"Already running on port {port}; opening browser.")
    else:
        try:
            port = start_server()
            print(f"Started on port {port}.")
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    if args.window:
        open_in_window(port)
    else:
        open_in_browser(port)
    return 0


if __name__ == "__main__":
    sys.exit(main())

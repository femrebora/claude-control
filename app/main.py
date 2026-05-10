"""
claude-control: local dashboard for managing ~/.claude/ assets.

Manages skills, plugins, agents, and commands installed under the user's
Claude Code config directory. Read/edit/toggle/add/remove/validate.

Security posture:
  - Binds to 127.0.0.1 by default (loopback only).
  - All filesystem operations are confined to CLAUDE_HOME via path resolution.
  - Uploaded ZIPs are validated against path traversal (Zip Slip).
  - No shell execution; subprocess used only for `git clone` with a fixed
    argument list and a strict URL regex.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

# --- Configuration -----------------------------------------------------------

CLAUDE_HOME = Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude")).resolve()
ASSET_KINDS: dict[str, str] = {
    "skills": "skills",
    "plugins": "plugins",
    "agents": "agents",
    "commands": "commands",
}
SETTINGS_FILE = CLAUDE_HOME / "settings.local.json"
GIT_URL_RE = re.compile(r"^(https://|git@)[\w./@:\-]+\.git$")

SkillState = Literal["on", "off", "name-only"]

BASE_DIR = Path(__file__).parent
app = FastAPI(title="claude-control", version="1.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


# --- Helpers (read CLAUDE_HOME/SETTINGS_FILE via module so tests can patch) ---

def _claude_home() -> Path:
    return sys.modules[__name__].CLAUDE_HOME


def _settings_file() -> Path:
    return sys.modules[__name__].SETTINGS_FILE


def _safe_join(base: Path, *parts: str) -> Path:
    candidate = (base / Path(*parts)).resolve()
    if base not in candidate.parents and candidate != base:
        raise HTTPException(status_code=400, detail="Path traversal blocked")
    return candidate


def _kind_dir(kind: str) -> Path:
    if kind not in ASSET_KINDS:
        raise HTTPException(status_code=404, detail=f"Unknown kind: {kind}")
    d = _claude_home() / ASSET_KINDS[kind]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_settings() -> dict:
    sf = _settings_file()
    if not sf.exists():
        return {}
    try:
        return json.loads(sf.read_text())
    except json.JSONDecodeError:
        return {}


def _write_settings(data: dict) -> None:
    sf = _settings_file()
    sf.parent.mkdir(parents=True, exist_ok=True)
    sf.write_text(json.dumps(data, indent=2))


def _split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
        return (fm if isinstance(fm, dict) else {}), m.group(2)
    except yaml.YAMLError:
        return {}, text


def _join_frontmatter(fm: dict, body: str) -> str:
    if not fm:
        return body
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{yaml_text}\n---\n\n{body.lstrip()}"


def _meta_path_for(entry: Path) -> Path | None:
    if entry.is_dir():
        for candidate in ("SKILL.md", "skill.md", "plugin.json", "README.md"):
            if (entry / candidate).exists():
                return entry / candidate
        return None
    if entry.suffix == ".md":
        return entry
    return None


def _dir_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                continue
    return total


def _normalize_tags(raw) -> list[str]:
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return []


def _scan_kind(kind: str) -> list[dict]:
    d = _kind_dir(kind)
    overrides = _read_settings().get("skillOverrides", {}) if kind == "skills" else {}
    out: list[dict] = []

    for entry in sorted(d.iterdir()):
        if entry.name.startswith("."):
            continue
        meta = _meta_path_for(entry)
        if meta is None:
            continue

        fm: dict = {}
        if meta.suffix == ".md":
            try:
                fm, _ = _split_frontmatter(meta.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                fm = {}

        name = fm.get("name", entry.stem)
        description = (fm.get("description") or "").strip()
        tags = _normalize_tags(fm.get("tags") or fm.get("categories") or [])

        state: SkillState = overrides.get(name, "on") if kind == "skills" else "on"

        try:
            stat = entry.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            size = _dir_size(entry)
        except OSError:
            modified = ""
            size = 0

        out.append({
            "name": name,
            "description": description[:240],
            "path": str(entry.relative_to(_claude_home())),
            "kind": kind,
            "state": state,
            "is_dir": entry.is_dir(),
            "tags": tags,
            "size": size,
            "modified": modified,
            "editable": meta.suffix == ".md",
        })
    return out


# --- Validation --------------------------------------------------------------

VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")


def _validate_skill(entry: Path) -> list[dict]:
    issues: list[dict] = []
    meta = _meta_path_for(entry)

    if meta is None:
        issues.append({"level": "error", "message": "No SKILL.md or README.md found"})
        return issues

    if meta.suffix != ".md":
        return issues

    try:
        text = meta.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        issues.append({"level": "error", "message": f"Cannot read {meta.name}: {e}"})
        return issues

    fm, body = _split_frontmatter(text)

    if not fm:
        issues.append({"level": "error", "message": "Missing YAML frontmatter (--- ... ---)"})
        return issues

    name = fm.get("name")
    if not name:
        issues.append({"level": "error", "message": "Missing required field: name"})
    elif not VALID_NAME_RE.match(str(name)):
        issues.append({
            "level": "warning",
            "message": f"Name '{name}' should be lowercase, hyphenated, 2-64 chars",
        })

    description = fm.get("description")
    if not description:
        issues.append({"level": "error", "message": "Missing required field: description"})
    elif len(str(description)) < 20:
        issues.append({"level": "warning", "message": "Description is very short (<20 chars)"})
    elif len(str(description)) > 1024:
        issues.append({"level": "warning", "message": "Description is very long (>1024 chars)"})

    if not body.strip():
        issues.append({"level": "warning", "message": "Skill body is empty"})

    if entry.is_dir() and entry.name != name:
        issues.append({
            "level": "info",
            "message": f"Folder '{entry.name}' differs from skill name '{name}'",
        })

    return issues


# --- Models ------------------------------------------------------------------

class FileEdit(BaseModel):
    frontmatter: dict
    body: str


# --- Routes ------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        context={"claude_home": str(_claude_home())},
    )


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "claude_home": str(_claude_home()), "exists": _claude_home().exists()}


@app.get("/api/assets")
def list_assets() -> dict:
    return {kind: _scan_kind(kind) for kind in ASSET_KINDS}


@app.get("/api/stats")
def stats() -> dict:
    out: dict = {}
    all_tags: set[str] = set()
    for kind in ASSET_KINDS:
        items = _scan_kind(kind)
        on_count = sum(1 for i in items if i["state"] == "on")
        out[kind] = {
            "total": len(items),
            "enabled": on_count,
            "disabled": len(items) - on_count,
            "total_size": sum(i["size"] for i in items),
        }
        for item in items:
            all_tags.update(item["tags"])
    out["claude_home"] = str(_claude_home())
    out["all_tags"] = sorted(all_tags)
    return out


@app.post("/api/skills/{name}/state")
def set_skill_state(name: str, state: str = Form(...)) -> dict:
    if state not in ("on", "off", "name-only"):
        raise HTTPException(status_code=400, detail="Invalid state")
    settings = _read_settings()
    overrides = settings.setdefault("skillOverrides", {})
    if state == "on":
        overrides.pop(name, None)
    else:
        overrides[name] = state
    _write_settings(settings)
    return {"ok": True, "name": name, "state": state}


@app.get("/api/{kind}/{name}/file")
def read_file(kind: str, name: str) -> dict:
    target = _safe_join(_kind_dir(kind), name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    meta = _meta_path_for(target)
    if meta is None or meta.suffix != ".md":
        raise HTTPException(status_code=400, detail="Not an editable markdown file")
    text = meta.read_text(encoding="utf-8", errors="replace")
    fm, body = _split_frontmatter(text)
    return {"path": str(meta.relative_to(_claude_home())), "frontmatter": fm, "body": body}


@app.get("/api/{kind}/{name}/preview")
def preview_file(kind: str, name: str) -> dict:
    """Return rendered HTML preview of a skill/agent/command markdown file."""
    target = _safe_join(_kind_dir(kind), name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    meta = _meta_path_for(target)
    if meta is None:
        raise HTTPException(status_code=400, detail="No previewable file")

    # Frontmatter card data
    fm: dict = {}
    body = ""
    if meta.suffix == ".md":
        text = meta.read_text(encoding="utf-8", errors="replace")
        fm, body = _split_frontmatter(text)

    # File listing for the asset folder (helps see scripts, references, etc.)
    files: list[dict] = []
    if target.is_dir():
        for p in sorted(target.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                rel = p.relative_to(target)
                try:
                    size = p.stat().st_size
                except OSError:
                    size = 0
                files.append({"path": str(rel), "size": size})

    return {
        "name": fm.get("name", target.stem),
        "description": fm.get("description", ""),
        "tags": _normalize_tags(fm.get("tags") or fm.get("categories") or []),
        "frontmatter": fm,
        "body": body,
        "meta_file": meta.name if meta else None,
        "files": files,
        "path": str(target.relative_to(_claude_home())),
    }


@app.put("/api/{kind}/{name}/file")
def write_file(kind: str, name: str, edit: FileEdit) -> dict:
    target = _safe_join(_kind_dir(kind), name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    meta = _meta_path_for(target)
    if meta is None or meta.suffix != ".md":
        raise HTTPException(status_code=400, detail="Not an editable markdown file")
    new_text = _join_frontmatter(edit.frontmatter, edit.body)
    tmp = meta.with_suffix(meta.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(meta)
    return {"ok": True, "path": str(meta.relative_to(_claude_home()))}


@app.get("/api/{kind}/{name}/validate")
def validate_asset(kind: str, name: str) -> dict:
    target = _safe_join(_kind_dir(kind), name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    issues = _validate_skill(target)
    return {"ok": all(i["level"] != "error" for i in issues), "issues": issues}


@app.delete("/api/{kind}/{name}")
def delete_asset(kind: str, name: str) -> dict:
    target = _safe_join(_kind_dir(kind), name)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Not found")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"ok": True, "deleted": name}


@app.post("/api/{kind}/upload")
async def upload_zip(kind: str, file: UploadFile = File(...)) -> dict:
    target_dir = _kind_dir(kind)
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Must be a .zip file")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            for member in zf.namelist():
                resolved = (target_dir / member).resolve()
                if target_dir not in resolved.parents and resolved != target_dir:
                    raise HTTPException(status_code=400, detail=f"Unsafe path in zip: {member}")
            zf.extractall(target_dir)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"ok": True, "extracted_to": str(target_dir)}


def _git_clone(url: str, dest: Path, depth: int = 1) -> None:
    if not GIT_URL_RE.match(url):
        raise HTTPException(status_code=400, detail="Invalid git URL (must end in .git)")
    try:
        subprocess.run(
            ["git", "clone", "--depth", str(depth), url, str(dest)],
            check=True,
            capture_output=True,
            timeout=180,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500, detail=f"git clone failed: {e.stderr.decode()[:300]}"
        ) from e
    except subprocess.TimeoutExpired as e:
        raise HTTPException(status_code=504, detail="git clone timed out") from e


@app.post("/api/{kind}/clone")
def clone_repo(kind: str, url: str = Form(...)) -> dict:
    target_dir = _kind_dir(kind)
    name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = _safe_join(target_dir, name)
    if dest.exists():
        raise HTTPException(status_code=409, detail=f"{name} already exists")
    _git_clone(url, dest)
    return {"ok": True, "cloned": name}


@app.post("/api/{kind}/bulk-import")
def bulk_import(kind: str, url: str = Form(...), subdir: str = Form("")) -> dict:
    """Clone a marketplace-style repo and copy each top-level folder under
    `subdir` (default: repo root) as a separate asset of `kind`."""
    target_dir = _kind_dir(kind)
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td) / "repo"
        _git_clone(url, scratch)
        candidate = (scratch / subdir).resolve() if subdir else scratch
        if candidate != scratch and scratch not in candidate.parents:
            raise HTTPException(status_code=400, detail=f"Invalid subdir: {subdir}")
        if not candidate.is_dir():
            raise HTTPException(status_code=400, detail=f"Subdir not found: {subdir}")

        imported: list[str] = []
        skipped: list[str] = []
        for child in sorted(candidate.iterdir()):
            if child.name.startswith(".") or child.name == "node_modules":
                continue
            if not child.is_dir():
                continue
            if _meta_path_for(child) is None:
                skipped.append(child.name)
                continue
            dest = target_dir / child.name
            if dest.exists():
                skipped.append(child.name)
                continue
            shutil.copytree(child, dest)
            imported.append(child.name)
    return {"ok": True, "imported": imported, "skipped": skipped}

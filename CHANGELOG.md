# Changelog

All notable changes to claude-control are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] — 2026-05-30

### Added
- **Trash management UI** — modal with restore and permanent-delete actions
- **Light/dark theme toggle** — persisted to `localStorage`
- **Sort controls** — dropdown for name, date, or size (ascending/descending)
- **Confirmation dialogs** — styled modals replace browser `confirm()`
- **Undo toast** — restore button appears after deletion
- **Tag autocomplete** — datalist populated from existing tags in edit/create modals
- **Keyboard shortcuts** — Ctrl+R to refresh; Enter/Space to open preview from focused card
- **Search result count** — shows match count when filtering
- **Debounced search** — 250ms input debounce to avoid layout thrashing
- 28 new tests (47 total, 82% coverage)

### Fixed
- Plugin delete button no longer shows for plugins with empty version field
- Malformed ZIP uploads return 400 instead of 500
- `starlette<1.0.0` pin added to `pyproject.toml`
- Orphaned `.tmp` files cleaned on startup
- `_kind_dir()` no longer creates directories on read-only GET routes
- Consolidated duplicate state-toggle routes
- `TRASH_DIR` is now runtime-computed (fixes test isolation)

### Changed
- Accessibility improvements: ARIA attributes on all modals, focus indicators, keyboard-navigable tags and cards, toast announcements
- Loading states during data fetches
- `on_event` replaced with lifespan handler (FastAPI best practice)

## [1.1.0] — 2026-05-10

### Added
- **Rich preview pane** — click any skill card name to open a rendered markdown preview with headings, code blocks, tables, and a file listing
- `GET /api/{kind}/{name}/preview` endpoint
- Markdown rendering via marked.js + DOMPurify (sanitized, no script execution)
- Esc-to-close on all modals

## [1.0.0] — 2026-05-10

### Added
- Local FastAPI dashboard for managing `~/.claude/` skills, plugins, agents, commands
- Toggle skills on / name-only / off (writes to `settings.local.json`)
- Inline edit modal for SKILL.md (frontmatter + body)
- Tag sidebar with click-to-filter
- Bulk import from marketplace repos (e.g. `anthropics/skills`)
- SKILL.md validator (frontmatter required-field + naming checks)
- Stats bar (per-kind counts and sizes)
- ZIP upload with Zip Slip protection
- `git clone` support with strict URL validation
- Cross-platform desktop installers
  - Linux: `install.sh` → `.desktop` entry + GNOME app database
  - macOS: `install-macos.sh` → `.app` bundle in `~/Applications/`
  - Windows: `install.ps1` → Start Menu shortcut
- Cross-platform launcher (`launcher.py`) with PID/port file management and idempotent re-launch
- Optional `pywebview` integration for native-window mode
- 19 pytest tests covering scan, toggle, edit, validate, delete, upload, and security paths
- GitHub Actions CI matrix on Python 3.10 / 3.11 / 3.12
- Pre-push secret scanner (`scripts/preflight.sh`)
- systemd unit for always-on home-server use

### Security
- Loopback-only bind by default (127.0.0.1)
- Path traversal blocked via `Path.resolve()` containment checks
- Zip Slip blocked at upload time
- No `shell=True` anywhere; subprocess calls use fixed argument lists
- 180-second timeout on all subprocess calls
- `git clone` URL validated against strict regex

[1.0.0]: https://github.com/YOUR_USER/claude-control/releases/tag/v1.0.0

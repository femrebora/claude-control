# claude-control

[![python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-A3E635)](LICENSE)

[![platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-555)](#install)
[![Linux](https://img.shields.io/badge/Linux-supported-A3E635?logo=linux&logoColor=white)](#ubuntu--linux-gnome-kde-xfce-cinnamon-mate)
[![macOS](https://img.shields.io/badge/macOS-supported-A3E635?logo=apple&logoColor=white)](#macos-12-monterey-or-newer)
[![Windows](https://img.shields.io/badge/Windows-supported-A3E635?logo=windows&logoColor=white)](#windows-10--11)

> A small, local dashboard for managing your Claude Code skills, plugins, agents, and commands. Runs as a real desktop app on Linux, macOS, and Windows. No terminal is needed after installation.

When you start collecting skills, you lose track of what's installed, what's on, what's stale. `claude-control` gives you one place to see and manage everything in your `~/.claude/` directory: toggle skills on or off, edit them inline, validate their frontmatter, bulk-import from marketplace repos, and add or remove with a click.

It runs entirely on your machine. No telemetry, no remote calls, no auth needed because it binds to `127.0.0.1` only.

![dashboard preview](assets/icon.png)

---

## Features

- **Browse** all skills, plugins, agents, and commands in one tabbed view
- **Click any skill name** to open a rendered markdown preview of its full SKILL.md
- **Stats bar** — live counts and sizes per category
- **Tag sidebar** — auto-generated from `tags:` frontmatter; click to filter
- **Tag autocomplete** — suggests existing tags when editing or creating assets
- **Toggle skills** — `on` / `name-only` / `off`, written to `settings.local.json`
- **Inline edit** — name, description, tags, and full markdown body in a modal
- **Validate** — lints SKILL.md frontmatter, flags missing fields and naming issues
- **Add** new skills via `.zip` upload or `git clone`
- **Bulk import** — clone a marketplace repo and import every folder as a separate skill
- **Search** by name, description, or tag (with debounced input and result count)
- **Sort** — by name, date, or size; ascending or descending
- **Trash** — soft-delete moves items to `~/.claude/.trash/`; restore or permanently delete via the trash modal
- **Undo** — toast notification with restore button after deletion
- **Light/dark theme** — toggle in the header, persisted across reloads
- **Keyboard navigation** — Tab through cards, Enter to preview, Ctrl+R to refresh, Esc to close modals
- **Styled confirmation dialogs** — replaces browser prompts with themed modals
- **Loading states** — visual feedback during data fetches
- **One-click Ubuntu / macOS / Windows app** — installers register it with your OS; click the icon to launch
- **Loopback-only** by default; never exposed to the network
- Zero JS frameworks, no build step, ~2,500 lines total

---

## Install

### Ubuntu / Linux (GNOME, KDE, XFCE, Cinnamon, MATE)

```bash
git clone https://github.com/femrebora/claude-control.git ~/claude-control
cd ~/claude-control
./install.sh
```

Press **Super**, type "Claude Control", click. Pin to dock by right-clicking the running icon.

### macOS (12 Monterey or newer)

```bash
git clone https://github.com/femrebora/claude-control.git ~/claude-control
cd ~/claude-control
./install-macos.sh
```

Builds a real `.app` bundle at `~/Applications/Claude Control.app`. Open it from Spotlight (⌘+Space → "Claude Control") or drag to the Dock.

### Windows 10 / 11

In **PowerShell**:

```powershell
git clone https://github.com/femrebora/claude-control.git $HOME\claude-control
cd $HOME\claude-control
.\install.ps1
```

If PowerShell complains about execution policy, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Press the Windows key, type "Claude Control", press Enter.

### Manual / dev install (any OS)

```bash
git clone https://github.com/femrebora/claude-control.git
cd claude-control
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows PowerShell
pip install -r requirements.txt
./run.sh                            # Linux/macOS
# python -m uvicorn app.main:app   # Windows
```

Open <http://127.0.0.1:8765>.

Full per-OS details, troubleshooting, and uninstall instructions: [`docs/DESKTOP_INSTALL.md`](docs/DESKTOP_INSTALL.md).

---

## Usage

### Previewing skills

Click any skill **name** (the heading on a card) to open a rich preview pane showing:

- The full description
- Tags
- The complete rendered SKILL.md body (headings, code blocks, tables, lists)
- A collapsible list of all files inside the skill folder

The preview pane has an **edit** button if you want to jump straight into editing. Press **Esc** to close it.

The markdown is rendered with [marked](https://marked.js.org/) and sanitized through [DOMPurify](https://github.com/cure53/DOMPurify) before being inserted into the DOM, so even malicious skill files can't inject script tags. Both libraries load from jsDelivr; if your network blocks CDNs, the preview falls back to plain text.

### Toggling skills

The card for each skill has three buttons: **on** / **name-only** / **off**. These map directly to Claude Code's `skillOverrides` setting:

| State | Effect |
|---|---|
| `on` | Fully active — Claude can invoke the skill |
| `name-only` | Claude sees the name and description only, not the body |
| `off` | Disabled — Claude ignores it |

Changes write to `~/.claude/settings.local.json` immediately. Claude Code picks them up on next session.

### Editing skills

Click **edit** on any skill card to open the inline editor. You can change the name, description, tags, and body. Click **validate** inside the editor to lint frontmatter before saving. **save** writes back to `SKILL.md` atomically.

### Tags

Add a `tags:` list to a skill's frontmatter and it'll appear in the sidebar:

```yaml
---
name: code-review 
description: Reviews a pull request and summarizes key issues.
tags:
  - git 
  - review
  - productivity
---
```

Click any tag to filter the grid.

### Adding new skills

Three ways:

1. **Drop a `.zip`** — click "upload .zip" and pick a file. Path traversal is blocked.
2. **`git clone`** — paste a `.git` URL.
3. **Bulk import** — paste a marketplace repo URL (e.g. `https://github.com/anthropics/skills.git`) and a subdirectory (`skills`). Every folder under that subdirectory becomes a separate skill.

### Validation

Validates SKILL.md against the conventions in the [official skills repo](https://github.com/anthropics/skills):

- Required: `name`, `description` in frontmatter
- `name` should be lowercase-hyphenated, 2–64 chars
- `description` should be 20–1024 chars
- Body shouldn't be empty
- Folder name should match the skill name

Reports as **error** / **warning** / **info**.

### Trash management

Deleting a skill, plugin, agent, or command moves it to `~/.claude/.trash/` — it's never permanently deleted unless you choose to. Click the **trash** button in the action bar to:

- View all trashed items with name, kind, size, and deletion date
- **Restore** any item back to its original location
- **Delete forever** to permanently remove it (after a confirmation prompt)

### Sorting

Use the dropdown in the action bar to sort cards by name (A–Z or Z–A), modification date (newest or oldest first), or size (largest or smallest first).

### Theme

Click the **light** / **dark** button in the header to switch between the editorial dark theme and a warm paper-inspired light theme. Your preference is saved and restored on next launch.

### Keyboard shortcuts

| Key | Action |
|---|---|
| `Ctrl+R` / `Cmd+R` | Refresh data |
| `Enter` or `Space` | Open preview for focused card |
| `Tab` | Move focus between cards, tags, and buttons |
| `Escape` | Close any open modal |

---

## Architecture

```
~/.claude/
├── skills/             ← managed
├── plugins/            ← managed (display-only; toggle via /plugin in CC)
├── agents/             ← managed
├── commands/           ← managed
├── .trash/             ← soft-deleted items (restore via trash modal)
└── settings.local.json ← skillOverrides written here

claude-control/
├── app/
│   ├── main.py            FastAPI routes + filesystem helpers (~560 lines)
│   ├── templates/
│   │   └── index.html     single-page UI (~220 lines)
│   └── static/
│       ├── style.css      editorial theme + light variant (~650 lines)
│       └── app.js         vanilla JS, no framework (~640 lines)
├── tests/                 pytest, 47 tests
├── launcher.py            cross-platform background server lifecycle
├── install.sh             Linux: registers .desktop entry
├── install-macos.sh       macOS: builds .app bundle in ~/Applications/
├── install.ps1            Windows: creates Start Menu shortcut
└── scripts/preflight.sh   pre-push secret scanner
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full request flow and extension points.

---

## API

All endpoints are local-only. Useful if you want to script against it:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness check |
| `GET` | `/api/assets` | List everything, all kinds |
| `GET` | `/api/stats` | Counts, sizes, all tags |
| `POST` | `/api/skills/{name}/state` | Toggle: form `state=on\|off\|name-only` |
| `GET` | `/api/{kind}/{name}/file` | Read frontmatter + body |
| `GET` | `/api/{kind}/{name}/preview` | Read + file listing for the rich preview pane |
| `PUT` | `/api/{kind}/{name}/file` | Write JSON `{frontmatter, body}` |
| `GET` | `/api/{kind}/{name}/validate` | Lint, return issues |
| `DELETE` | `/api/{kind}/{name}` | Remove asset |
| `POST` | `/api/{kind}/upload` | Multipart `.zip` upload |
| `POST` | `/api/{kind}/clone` | Form `url=<repo>.git` |
| `POST` | `/api/{kind}/bulk-import` | Form `url=<repo>.git&subdir=<path>` |

OpenAPI spec is auto-generated at <http://127.0.0.1:8765/docs>.

---

## Configuration

All config via environment variables (see [`.env.example`](.env.example)):

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_HOME` | `~/.claude` | Directory to manage |
| `HOST` | `127.0.0.1` | Bind address — keep on loopback |
| `PORT` | `8765` | Port |

To manage a project-local `.claude/` instead of your home one:

```bash
CLAUDE_HOME=/path/to/project/.claude ./run.sh
```

---

## Run on boot (Beelink, NUC, home server)

If you want it always available on a home server:

```bash
# After install.sh, also copy the systemd unit
mkdir -p ~/.config/systemd/user
cp docs/systemd/claude-control.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claude-control
```

To survive logouts: `sudo loginctl enable-linger $USER`.

For LAN access from another machine, **don't** rebind to `0.0.0.0` — use SSH port forwarding:

```bash
ssh -L 8765:127.0.0.1:8765 user@your-server.local
```

Full details in [`docs/SYSTEMD.md`](docs/SYSTEMD.md).

---

## Security

claude-control has **no authentication**. The threat model assumes you are the only user on the machine and the server is on loopback. With those assumptions, it's safe.

Hardening that's already in place:

- Loopback bind by default; warning printed if you override
- Path traversal blocked via `Path.resolve()` checks
- Zip Slip blocked at upload time
- No `shell=True` anywhere
- `git clone` URLs validated against a strict regex
- 180-second timeout on all subprocess calls

What you must NOT do:

- Bind to `0.0.0.0` without an authenticated reverse proxy in front
- Run as `root`
- Install untrusted skills (this app helps you manage them, but skills can contain arbitrary executable instructions for Claude)

Full threat model and pre-publication checklist: [`SECURITY.md`](SECURITY.md).

Reporting a vulnerability: open a [GitHub Security Advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability), not a public issue.

---

## Development

```bash
git clone https://github.com/femrebora/claude-control.git
cd claude-control
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Test against an isolated fake claude home (won't touch your real one)
mkdir -p test-claude-home/{skills,plugins,agents,commands}
CLAUDE_HOME="$PWD/test-claude-home" ./run.sh
```

Run tests and lint:

```bash
pytest                      # 19 tests, ~1s
ruff check app tests        # lint
ruff format app tests       # auto-format
bash scripts/preflight.sh   # secret scan before push
```

CI runs all three on every push (Python 3.10 / 3.11 / 3.12). See [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Pushing your fork to GitHub

Before `git push`, **always** run:

```bash
bash scripts/preflight.sh
```

It refuses to pass if it detects:
- tracked `.env` files (other than `.env.example`)
- tracked `settings.local.json` or `.claude/` directory
- common API key patterns (Anthropic, AWS, GitHub PAT)
- missing or incomplete `.gitignore`

If you want extra protection on GitHub, in repo Settings → Code security:
- Enable **Secret scanning**
- Enable **Push protection**
- Enable **Dependabot alerts**

---

PRs welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Uninstalling

> **Always run the uninstall script before deleting the project folder.**
> The script stops the running server, removes the desktop entry / app bundle / Start Menu shortcut, and refreshes the system icon cache. If you delete the project folder first, you'll be left with an orphaned launcher icon that points nowhere — see [Recovery](#recovery-i-already-deleted-the-folder) below.
>
> The uninstaller **never** touches `~/.claude/` (your skills, plugins, agents, commands, and settings). Reinstalling later picks up exactly where you left off.

### Linux

```bash
cd ~/claude-control
./uninstall.sh
```

### macOS

```bash
cd ~/claude-control
./uninstall-macos.sh
```

### Windows (PowerShell)

```powershell
cd $HOME\claude-control
.\uninstall.ps1
```

After the uninstaller finishes, the project folder is no longer registered with your OS and can be deleted whenever you like with your normal file manager (Files / Finder / Explorer). Nothing on your system references it anymore.

### Recovery: I already deleted the folder

If you removed the project folder before running the uninstaller, the desktop launcher entry and icon are now orphaned. Remove them by hand:

**Linux**

```bash
rm -f ~/.local/share/applications/claude-control.desktop
rm -f ~/.local/share/icons/hicolor/256x256/apps/claude-control.png
update-desktop-database ~/.local/share/applications 2>/dev/null || true
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor 2>/dev/null || true
```

**macOS**

```bash
rm -rf "$HOME/Applications/Claude Control.app"
```

**Windows (PowerShell)**

```powershell
Remove-Item "$HOME\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Claude Control.lnk" -ErrorAction SilentlyContinue
```

Your `~/.claude/` directory is preserved regardless.

---

## License

[MIT](LICENSE).

## Related

- [anthropics/skills](https://github.com/anthropics/skills) — official Anthropic skills

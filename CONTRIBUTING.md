# Contributing

Thanks for considering a contribution. claude-control aims to stay small and focused — please read this before opening a large PR.

## Scope

claude-control **manages** local Claude Code assets. It does not:

- Execute skills or run user code (that's Claude Code's job)
- Authenticate users (it's a localhost tool)
- Sync to cloud or remote registries (yet — see roadmap)
- Edit skill bodies (yet — see roadmap)

If your idea fits the existing scope, go ahead. If it expands the scope, open an issue first.

## Dev setup

```bash
git clone https://github.com/YOUR_USER/claude-control.git
cd claude-control
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
./run.sh
```

For testing without touching your real `~/.claude/`:

```bash
mkdir -p test-claude-home/{skills,plugins,agents,commands}
CLAUDE_HOME="$PWD/test-claude-home" ./run.sh
```

## Code style

- Python: format with `ruff format`, lint with `ruff check`.
- JS / HTML / CSS: vanilla, no build step. Keep it that way.
- Type hints on every Python function signature.
- No new runtime dependencies without discussion.

## Pull requests

1. Fork and branch from `main`
2. Add a test if you change behavior (we use `pytest`)
3. Run `ruff check && ruff format --check --diff && pytest`
4. Run `bash scripts/preflight.sh` to scan for secrets before pushing
5. Reference the issue your PR closes
6. Keep PRs focused — one feature or fix per PR

Or use the Makefile: `make lint && make test`

## Reporting bugs

Open an issue with:

- OS and Python version
- Steps to reproduce
- Expected vs. actual behavior
- Anything in the uvicorn console output

## Security issues

See [`SECURITY.md`](SECURITY.md) — please **don't** open public issues for security bugs.

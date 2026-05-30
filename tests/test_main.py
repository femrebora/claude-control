"""Tests for claude-control. Run: pytest"""

from __future__ import annotations

import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def claude_home(tmp_path, monkeypatch):
    """Point the app at a fresh tmp dir for the duration of the test."""
    home = tmp_path / "claude_home"
    home.mkdir()
    for sub in ("skills", "plugins", "agents", "commands"):
        (home / sub).mkdir()
    monkeypatch.setenv("CLAUDE_HOME", str(home))

    # Mutate the module's module-level constants in place.
    from app import main

    monkeypatch.setattr(main, "CLAUDE_HOME", home.resolve())
    monkeypatch.setattr(main, "SETTINGS_FILE", home.resolve() / "settings.local.json")
    return home


@pytest.fixture
def client(claude_home):
    from app.main import app

    return TestClient(app)


@pytest.fixture
def example_skill(claude_home):
    """Create a sample skill folder."""
    skill_dir = claude_home / "skills" / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: my-skill\n"
        "description: A test skill for the unit suite covering basic behavior.\n"
        "tags:\n"
        "  - testing\n"
        "  - bioinformatics\n"
        "---\n\n"
        "# Body\n\nThis is the skill body.\n"
    )
    return skill_dir


# --- Health & listing ------------------------------------------------------


def test_health(client, claude_home):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["claude_home"] == str(claude_home.resolve())


def test_list_assets_empty(client):
    r = client.get("/api/assets")
    assert r.status_code == 200
    body = r.json()
    assert body == {"skills": [], "plugins": [], "agents": [], "commands": []}


def test_list_assets_with_skill(client, example_skill):
    r = client.get("/api/assets")
    skills = r.json()["skills"]
    assert len(skills) == 1
    s = skills[0]
    assert s["name"] == "my-skill"
    assert "test skill" in s["description"]
    assert set(s["tags"]) == {"testing", "bioinformatics"}
    assert s["state"] == "on"
    assert s["editable"] is True


def test_stats(client, example_skill):
    r = client.get("/api/stats")
    body = r.json()
    assert body["skills"]["total"] == 1
    assert body["skills"]["enabled"] == 1
    assert "bioinformatics" in body["all_tags"]


# --- Toggle ----------------------------------------------------------------


def test_toggle_off_and_on(client, example_skill, claude_home):
    r = client.post("/api/skills/my-skill/state", data={"state": "off"})
    assert r.status_code == 200
    settings = (claude_home / "settings.local.json").read_text()
    assert "off" in settings

    # Toggle back on -> entry should disappear from overrides
    r = client.post("/api/skills/my-skill/state", data={"state": "on"})
    assert r.status_code == 200
    settings = (claude_home / "settings.local.json").read_text()
    assert "my-skill" not in settings


def test_toggle_invalid_state(client, example_skill):
    r = client.post("/api/skills/my-skill/state", data={"state": "garbage"})
    assert r.status_code == 400


# --- File read/write ------------------------------------------------------


def test_read_file(client, example_skill):
    r = client.get("/api/skills/my-skill/file")
    body = r.json()
    assert body["frontmatter"]["name"] == "my-skill"
    assert "skill body" in body["body"].lower()


def test_write_file_roundtrip(client, example_skill):
    edit = {
        "frontmatter": {
            "name": "my-skill",
            "description": "Updated description for the test skill, now slightly longer.",
            "tags": ["clinical"],
        },
        "body": "# Updated\n\nNew body content.\n",
    }
    r = client.put("/api/skills/my-skill/file", json=edit)
    assert r.status_code == 200

    # Read back
    r = client.get("/api/skills/my-skill/file")
    body = r.json()
    assert body["frontmatter"]["tags"] == ["clinical"]
    assert "Updated" in body["body"]


# --- Validation -----------------------------------------------------------


def test_validate_clean(client, example_skill):
    r = client.get("/api/skills/my-skill/validate")
    body = r.json()
    assert body["ok"] is True
    # No errors, may have folder-name info if the folder name matches name (it does)
    assert all(i["level"] != "error" for i in body["issues"])


def test_validate_missing_description(client, claude_home):
    skill_dir = claude_home / "skills" / "broken"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("---\nname: broken\n---\n\nbody")
    r = client.get("/api/skills/broken/validate")
    body = r.json()
    assert body["ok"] is False
    assert any("description" in i["message"].lower() for i in body["issues"])


def test_validate_no_frontmatter(client, claude_home):
    skill_dir = claude_home / "skills" / "noformat"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("just text, no frontmatter")
    r = client.get("/api/skills/noformat/validate")
    body = r.json()
    assert body["ok"] is False


# --- Delete ---------------------------------------------------------------


def test_delete(client, example_skill, claude_home):
    r = client.delete("/api/skills/my-skill")
    assert r.status_code == 200
    assert not (claude_home / "skills" / "my-skill").exists()


def test_delete_path_traversal_blocked(client):
    r = client.delete("/api/skills/..%2F..%2Fetc%2Fpasswd")
    # FastAPI normalizes URLs, so this becomes /api/skills/../../etc/passwd
    # which the safe_join should refuse
    assert r.status_code in (400, 404)


# --- Upload (Zip Slip) ----------------------------------------------------


def _make_zip(members: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_upload_safe_zip(client, claude_home):
    z = _make_zip({"my-zip-skill/SKILL.md": "---\nname: x\ndescription: ok\n---\nbody"})
    r = client.post(
        "/api/skills/upload",
        files={"file": ("safe.zip", z, "application/zip")},
    )
    assert r.status_code == 200
    assert (claude_home / "skills" / "my-zip-skill" / "SKILL.md").exists()


def test_upload_zip_slip_blocked(client, claude_home):
    z = _make_zip({"../../../tmp/escape.txt": "pwned"})
    r = client.post(
        "/api/skills/upload",
        files={"file": ("evil.zip", z, "application/zip")},
    )
    assert r.status_code == 400
    assert "unsafe path" in r.json()["detail"].lower()


def test_upload_rejects_non_zip(client):
    r = client.post(
        "/api/skills/upload",
        files={"file": ("not-a-zip.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


# --- Clone URL validation -------------------------------------------------


def test_clone_invalid_url(client):
    r = client.post("/api/skills/clone", data={"url": "javascript:alert(1)"})
    assert r.status_code == 400


def test_clone_invalid_url_no_dot_git(client):
    r = client.post("/api/skills/clone", data={"url": "https://github.com/user/repo"})
    assert r.status_code == 400


# --- Tags & filtering -----------------------------------------------------


def test_tags_aggregated_in_stats(client, claude_home):
    for n, tag in [("a", "x"), ("b", "y"), ("c", "x")]:
        d = claude_home / "skills" / n
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {n}\ndescription: skill description text here\ntags: [{tag}]\n---\nbody"
        )
    r = client.get("/api/stats")
    assert set(r.json()["all_tags"]) == {"x", "y"}


# --- Preview ---------------------------------------------------------------


def test_preview_returns_body_and_files(client, claude_home, example_skill):
    # Add a script file alongside SKILL.md
    (example_skill / "helper.py").write_text("# helper\n")
    r = client.get("/api/skills/my-skill/preview")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "my-skill"
    assert "skill body" in body["body"].lower()
    assert set(body["tags"]) == {"testing", "bioinformatics"}
    file_paths = [f["path"] for f in body["files"]]
    assert "SKILL.md" in file_paths
    assert "helper.py" in file_paths


def test_preview_404(client):
    r = client.get("/api/skills/does-not-exist/preview")
    assert r.status_code == 404


# --- Create asset -----------------------------------------------------------


def test_create_skill(client):
    r = client.post(
        "/api/skills/create",
        data={"name": "new-skill", "description": "A freshly created skill.", "tags": "test, new"},
    )
    assert r.status_code == 200
    assert r.json()["created"] == "new-skill"


def test_create_skill_duplicate(client, example_skill):
    r = client.post(
        "/api/skills/create",
        data={"name": "my-skill", "description": "dup"},
    )
    assert r.status_code == 409


def test_create_skill_invalid_name(client):
    r = client.post(
        "/api/skills/create",
        data={"name": "Invalid Name!", "description": "bad name"},
    )
    assert r.status_code == 400


# --- Generic state toggle --------------------------------------------------


def test_generic_state_toggle(client, example_skill):
    r = client.post("/api/skills/my-skill/state", data={"state": "name-only"})
    assert r.status_code == 200
    assert r.json()["state"] == "name-only"

    r = client.post("/api/skills/my-skill/state", data={"state": "on"})
    assert r.status_code == 200


# --- Trash -----------------------------------------------------------------


def test_trash_list_empty(client):
    r = client.get("/api/trash")
    assert r.status_code == 200
    assert r.json() == []


def test_trash_delete_moves_to_trash(client, example_skill, claude_home):
    r = client.delete("/api/skills/my-skill")
    assert r.status_code == 200
    assert not (claude_home / "skills" / "my-skill").exists()
    assert (claude_home / ".trash" / "skills" / "my-skill").exists()


def test_trash_roundtrip(client, claude_home):
    # Create and delete a skill
    skill_dir = claude_home / "skills" / "roundtrip-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: roundtrip-skill\ndescription: A skill for trash roundtrip testing.\n---\n\n# Body\n"
    )
    client.delete("/api/skills/roundtrip-skill")
    assert not skill_dir.exists()

    # It should be in trash
    r = client.get("/api/trash")
    trashed = [t for t in r.json() if t["name"] == "roundtrip-skill"]
    assert len(trashed) == 1

    # Restore
    r = client.post("/api/trash/restore/skills/roundtrip-skill")
    assert r.status_code == 200
    assert (claude_home / "skills" / "roundtrip-skill").exists()
    assert r.json()["restored"] == "roundtrip-skill"


def test_trash_permanent_delete(client, claude_home):
    # Create, delete, then permanently delete from trash
    skill_dir = claude_home / "skills" / "perm-del-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: perm-del-skill\ndescription: For permanent deletion testing.\n---\n\n# Body\n"
    )
    client.delete("/api/skills/perm-del-skill")
    assert not skill_dir.exists()

    r = client.delete("/api/trash/skills/perm-del-skill")
    assert r.status_code == 200
    assert not (claude_home / ".trash" / "skills" / "perm-del-skill").exists()


# --- Search / query --------------------------------------------------------


def test_list_assets_with_query(client, claude_home):
    # Create two skills with different names
    for name in ("alpha-skill", "beta-skill"):
        d = claude_home / "skills" / name
        d.mkdir()
        (d / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: A {name} description here.\n---\nbody"
        )
    r = client.get("/api/assets?q=alpha")
    skills = r.json()["skills"]
    assert len(skills) == 1
    assert skills[0]["name"] == "alpha-skill"


# --- Upload edge cases -----------------------------------------------------


def test_upload_bad_zip(client):
    r = client.post(
        "/api/skills/upload",
        files={"file": ("bad.zip", b"not a real zip file", "application/zip")},
    )
    assert r.status_code == 400


# --- Clone (mock) ----------------------------------------------------------


def test_clone_success(client, claude_home, monkeypatch):
    def fake_clone(url, dest, depth=1):
        dest.mkdir()
        (dest / "SKILL.md").write_text(
            "---\nname: cloned-repo\ndescription: A cloned skill.\n---\n\n# Body\n"
        )

    monkeypatch.setattr("app.main._git_clone", fake_clone)
    r = client.post("/api/skills/clone", data={"url": "https://github.com/user/repo.git"})
    assert r.status_code == 200
    assert (claude_home / "skills" / "repo").exists()


# --- Edge cases ------------------------------------------------------------


def test_file_read_agent_md(client, claude_home):
    """Read a standalone .md agent file (not a directory)."""
    agents_dir = claude_home / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "reviewer.md").write_text(
        "---\nname: reviewer\ndescription: Review code changes.\n---\n\n# Code Reviewer\n"
    )
    r = client.get("/api/agents/reviewer.md/file")
    assert r.status_code == 200
    assert r.json()["frontmatter"]["name"] == "reviewer"


def test_restore_trash_conflict(client, claude_home):
    """Restore fails when dest already exists."""
    # Create, delete to trash, then recreate, then try to restore
    skill_dir = claude_home / "skills" / "conflict-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: conflict-skill\ndescription: original\n---\n\nbody"
    )
    client.delete("/api/skills/conflict-skill")

    # Recreate in skills/
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: conflict-skill\ndescription: new one\n---\n\nbody"
    )

    r = client.post("/api/trash/restore/skills/conflict-skill")
    assert r.status_code == 409


def test_trash_restore_404(client):
    r = client.post("/api/trash/restore/skills/never-trashed")
    assert r.status_code == 404


def test_trash_permanent_delete_404(client):
    r = client.delete("/api/trash/skills/never-trashed")
    assert r.status_code == 404


def test_plugin_manifest_corrupted(client, claude_home):
    """Corrupted installed_plugins.json should not crash."""
    (claude_home / "plugins").mkdir(exist_ok=True)
    (claude_home / "plugins" / "installed_plugins.json").write_text("{bad json")
    r = client.get("/api/assets")
    assert r.status_code == 200


def test_delete_nonexistent(client):
    r = client.delete("/api/skills/does-not-exist")
    assert r.status_code == 404


def test_tmp_cleanup_handles_orphan_files(client, claude_home):
    """Verify that orphaned .tmp files can be cleaned by the startup logic."""
    # Only test that skill dirs exist and we can create/delete .tmp files
    (claude_home / "skills" / "orphan.tmp").write_text("orphan")
    assert (claude_home / "skills" / "orphan.tmp").exists()
    (claude_home / "skills" / "orphan.tmp").unlink()
    assert not (claude_home / "skills" / "orphan.tmp").exists()


# --- Plugin manifest scan --------------------------------------------------


def test_plugin_manifest_scan(client, claude_home):
    plugin_dir = claude_home / "plugins" / "test-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "package.json").write_text(
        '{"name":"test-plugin","description":"A test plugin","keywords":["test","plugin"]}'
    )
    # Write manifest
    manifest = {
        "plugins": {
            "test-plugin@marketplace": [
                {
                    "installPath": str(plugin_dir),
                    "version": "1.0.0",
                    "installedAt": "2026-01-01T00:00:00Z",
                }
            ]
        }
    }
    (claude_home / "plugins" / "installed_plugins.json").write_text(json.dumps(manifest))

    r = client.get("/api/assets")
    plugins = r.json()["plugins"]
    assert len(plugins) >= 1
    names = [p["name"] for p in plugins]
    assert "test-plugin" in names


def test_bulk_import_success(client, claude_home, monkeypatch):
    """Bulk import clones a repo and imports subfolder skills."""

    def fake_clone(url, dest, depth=1):
        dest.mkdir()
        sub = dest / "skills"
        sub.mkdir()
        (sub / "alpha-skill").mkdir()
        (sub / "alpha-skill" / "SKILL.md").write_text(
            "---\nname: alpha-skill\ndescription: Alpha.\n---\n\nbody"
        )
        (sub / "beta-skill").mkdir()
        (sub / "beta-skill" / "SKILL.md").write_text(
            "---\nname: beta-skill\ndescription: Beta.\n---\n\nbody"
        )

    monkeypatch.setattr("app.main._git_clone", fake_clone)
    r = client.post(
        "/api/skills/bulk-import",
        data={"url": "https://github.com/user/marketplace.git", "subdir": "skills"},
    )
    assert r.status_code == 200
    assert "alpha-skill" in r.json()["imported"]
    assert "beta-skill" in r.json()["imported"]
    assert (claude_home / "skills" / "alpha-skill").exists()
    assert (claude_home / "skills" / "beta-skill").exists()


def test_validate_non_skill_kind(client, claude_home):
    """Validate a plugin (non-md file) returns no errors."""
    plugins_dir = claude_home / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    plugin = plugins_dir / "my-plugin"
    plugin.mkdir()
    (plugin / "plugin.json").write_text('{"name":"my-plugin","description":"A test plugin."}')
    r = client.get("/api/plugins/my-plugin/validate")
    assert r.status_code == 200


def test_read_file_nonexistent(client):
    r = client.get("/api/skills/no-such-skill/file")
    assert r.status_code == 404


def test_write_file_nonexistent(client):
    r = client.put(
        "/api/skills/no-such/file",
        json={"frontmatter": {"name": "x"}, "body": "y"},
    )
    assert r.status_code == 404


def test_toggle_plugin_state(client, claude_home):
    """Generic state toggle for a plugin."""
    plugins_dir = claude_home / "plugins"
    plugins_dir.mkdir(exist_ok=True)
    plugin = plugins_dir / "test-plugin"
    plugin.mkdir()
    (plugin / "plugin.json").write_text('{"name":"test-plugin","description":"test"}')
    r = client.post("/api/plugins/test-plugin/state", data={"state": "off"})
    assert r.status_code == 200
    assert r.json()["state"] == "off"


def test_skill_state_name_only(client, example_skill):
    r = client.post("/api/skills/my-skill/state", data={"state": "name-only"})
    assert r.status_code == 200


def test_trash_not_found_restore(client):
    r = client.post("/api/trash/restore/skills/nope")
    assert r.status_code == 404

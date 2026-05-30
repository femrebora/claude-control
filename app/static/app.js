// claude-control — vanilla JS, no build step.

const state = {
  kind: "skills",
  query: "",
  selectedTag: null,
  sortBy: "name",
  sortDir: 1,
  loading: false,
  data: { skills: [], plugins: [], agents: [], commands: [] },
  stats: null,
};

const $ = (id) => document.getElementById(id);
const grid = $("grid");
const sidebar = $("tag-list");
const statsEl = $("stats");
const filterInput = $("filter");
const tabs = $("tabs");
const zipUpload = $("zip-upload");
const cloneBtn = $("clone-btn");
const bulkBtn = $("bulk-btn");
const refreshBtn = $("refresh-btn");
const trashBtn = $("trash-btn");
const themeToggle = $("theme-toggle");
const sortSelect = $("sort-select");

// --- API helper ---
async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error((data && data.detail) || res.statusText);
  return data;
}

async function refresh() {
  state.loading = true;
  renderGrid();
  try {
    const [assets, statsData] = await Promise.all([api("/api/assets"), api("/api/stats")]);
    state.data = assets;
    state.stats = statsData;
    renderStats();
    renderTags();
    renderGrid();
  } catch (e) {
    toast("Failed to load: " + e.message, "error");
  } finally {
    state.loading = false;
    renderGrid();
  }
}

// --- Rendering ---

function renderStats() {
  if (!state.stats) return;
  const kinds = ["skills", "plugins", "agents", "commands"];
  statsEl.innerHTML = kinds.map((k) => {
    const s = state.stats[k];
    return `
      <div class="stat-cell">
        <div class="label">${k}</div>
        <div class="value">${s.total}</div>
        <div class="sub">${s.enabled} on · ${s.disabled} off · ${formatBytes(s.total_size)}</div>
      </div>`;
  }).join("");
}

function renderTags() {
  const tags = state.stats?.all_tags || [];
  if (tags.length === 0) {
    sidebar.innerHTML = '<div class="tag-empty">no tags yet — add <code>tags:</code> to a SKILL.md frontmatter</div>';
    return;
  }
  const allClass = state.selectedTag === null ? "tag-pill active" : "tag-pill";
  const html = [`<div class="${allClass}" data-tag="" tabindex="0" role="button" aria-pressed="${state.selectedTag === null}">all</div>`].concat(
    tags.map((t) => {
      const cls = state.selectedTag === t ? "tag-pill active" : "tag-pill";
      return `<div class="${cls}" data-tag="${escapeAttr(t)}" tabindex="0" role="button" aria-pressed="${state.selectedTag === t}">${escapeHtml(t)}</div>`;
    })
  );
  sidebar.innerHTML = html.join("");
}

function renderGrid() {
  let items = state.data[state.kind] || [];

  // Loading skeleton
  if (state.loading && items.length === 0) {
    grid.innerHTML = `<div class="empty">loading…</div>`;
    return;
  }

  if (state.query) {
    const q = state.query.toLowerCase();
    items = items.filter(
      (it) =>
        it.name.toLowerCase().includes(q) ||
        (it.description || "").toLowerCase().includes(q) ||
        it.tags.some((t) => t.toLowerCase().includes(q))
    );
  }
  if (state.selectedTag) {
    items = items.filter((it) => it.tags.includes(state.selectedTag));
  }

  // Sort
  items = [...items].sort((a, b) => {
    switch (state.sortBy) {
      case "name": return state.sortDir * a.name.localeCompare(b.name);
      case "modified": return state.sortDir * ((new Date(b.modified || 0)).getTime() - (new Date(a.modified || 0)).getTime());
      case "size": return state.sortDir * (b.size - a.size);
      default: return 0;
    }
  });

  const filterActive = !!(state.query || state.selectedTag);
  let countHtml = "";
  if (filterActive) {
    countHtml = `<div class="result-count">${items.length} ${state.kind} found</div>`;
  }

  if (items.length === 0) {
    const msg = filterActive
      ? `no ${state.kind} match the current filter`
      : `no ${state.kind} yet`;
    grid.innerHTML = countHtml + `<div class="empty">${msg}</div>`;
    return;
  }
  grid.innerHTML = countHtml + items.map(card).join("");
}

function basenameFromPath(path) {
  // path is like "skills/example-skill" or "agents/code-reviewer.md"
  const segs = path.split("/");
  return segs.slice(1).join("/") || segs.pop();
}

function card(it) {
  const stateClass = `state-${it.state.replace(" ", "-")}`;
  const isSkill = it.kind === "skills";
  const isPlugin = it.kind === "plugins";
  const desc = it.description ? escapeHtml(it.description) : '<em style="opacity:0.5">no description</em>';
  const tagsHtml = it.tags.length
    ? `<div class="card-tags">${it.tags.map((t) => `<span class="tag-pill">${escapeHtml(t)}</span>`).join("")}</div>`
    : "";
  const meta = `<div class="card-meta"><span>${formatBytes(it.size)}</span><span>${formatDate(it.modified)}</span></div>`;

  const pluginInfo = isPlugin && (it.version || it.marketplace)
    ? `<div class="card-meta"><span>v${escapeHtml(it.version || "?")}</span><span>@${escapeHtml(it.marketplace || "?")}</span></div>` : "";

  const base = basenameFromPath(it.path);

  let stateButtons = "";
  if (isSkill) {
    stateButtons = `
      <button class="btn" data-act="state" data-state="on" data-name="${escapeAttr(it.name)}" data-kind="${it.kind}">on</button>
      <button class="btn" data-act="state" data-state="name-only" data-name="${escapeAttr(it.name)}" data-kind="${it.kind}">name-only</button>
      <button class="btn" data-act="state" data-state="off" data-name="${escapeAttr(it.name)}" data-kind="${it.kind}">off</button>`;
  } else if (isPlugin) {
    stateButtons = `
      <button class="btn" data-act="state" data-state="on" data-name="${escapeAttr(it.name)}" data-kind="${it.kind}">on</button>
      <button class="btn" data-act="state" data-state="off" data-name="${escapeAttr(it.name)}" data-kind="${it.kind}">off</button>`;
  }

  const editBtn = it.editable
    ? `<button class="btn" data-act="edit" data-kind="${it.kind}" data-base="${escapeAttr(base)}">edit</button>` : "";
  const validateBtn = it.editable
    ? `<button class="btn" data-act="validate" data-kind="${it.kind}" data-base="${escapeAttr(base)}" data-name="${escapeAttr(it.name)}">validate</button>` : "";

  return `
    <article class="card" data-kind="${it.kind}" data-base="${escapeAttr(base)}">
      <div class="card-header">
        <h3 class="card-name" title="Click to preview" tabindex="0" role="button">${escapeHtml(it.name)}</h3>
        <span class="card-state ${stateClass}">${it.state}</span>
      </div>
      <p class="card-desc">${desc}</p>
      ${tagsHtml}
      ${meta}
      ${pluginInfo}
      <div class="card-path">${escapeHtml(it.path)}</div>
      <div class="card-footer">
        ${stateButtons}
        ${editBtn}
        ${validateBtn}
        ${(isPlugin) ? "" : `<button class="btn danger" data-act="delete" data-kind="${it.kind}" data-base="${escapeAttr(base)}" data-path="${escapeAttr(it.path)}">delete</button>`}
      </div>
    </article>`;
}

// --- Helpers ---
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }
function formatBytes(n) {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${units[i]}`;
}
function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const days = Math.floor((new Date() - d) / 86400000);
    if (days === 0) return "today";
    if (days === 1) return "yesterday";
    if (days < 30) return `${days}d ago`;
    return d.toISOString().slice(0, 10);
  } catch { return ""; }
}

function populateTagDatalist(inputId, listId) {
  let dl = $(listId);
  if (!dl) {
    dl = document.createElement("datalist");
    dl.id = listId;
    $(inputId).setAttribute("list", listId);
    $(inputId).after(dl);
  }
  dl.innerHTML = (state.stats?.all_tags || []).map(t => `<option value="${escapeHtml(t)}">`).join("");
}

// Safe markdown rendering: marked → HTML, then DOMPurify scrubs it
function renderMarkdown(md) {
  if (typeof marked === "undefined" || typeof DOMPurify === "undefined") {
    return `<pre>${escapeHtml(md)}</pre>`;  // fallback if CDN blocked
  }
  marked.setOptions({ breaks: false, gfm: true });
  const dirty = marked.parse(md || "");
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ["p","br","strong","em","u","s","code","pre","blockquote","ul","ol","li",
                   "h1","h2","h3","h4","h5","h6","a","table","thead","tbody","tr","th","td",
                   "hr","img","del"],
    ALLOWED_ATTR: ["href","title","alt","src","class"],
  });
}

// --- Tab/filter/sidebar events ---

tabs.addEventListener("click", (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  state.kind = btn.dataset.kind;
  renderGrid();
});

let filterTimer = null;
filterInput.addEventListener("input", (e) => {
  clearTimeout(filterTimer);
  filterTimer = setTimeout(() => {
    state.query = e.target.value;
    renderGrid();
  }, 250);
});

sidebar.addEventListener("click", (e) => {
  const el = e.target.closest(".tag-pill");
  if (!el) return;
  state.selectedTag = el.dataset.tag === "" ? null : el.dataset.tag;
  renderTags();
  renderGrid();
});

sidebar.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    const el = e.target.closest(".tag-pill");
    if (!el) return;
    e.preventDefault();
    state.selectedTag = el.dataset.tag === "" ? null : el.dataset.tag;
    renderTags();
    renderGrid();
  }
});

// --- Card click (preview or buttons) ---

grid.addEventListener("click", async (e) => {
  // Card name click → open preview
  const nameEl = e.target.closest(".card-name");
  if (nameEl) {
    const card = nameEl.closest(".card");
    if (card?.dataset.kind && card?.dataset.base) {
      openPreview(card.dataset.kind, card.dataset.base);
    }
    return;
  }

  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const act = btn.dataset.act;
  const kind = btn.dataset.kind;
  const base = btn.dataset.base;
  const name = btn.dataset.name;

  try {
    if (act === "state") {
      const fd = new FormData();
      fd.append("state", btn.dataset.state);
      const stateKind = btn.dataset.kind || "skills";
	      await api(`/api/${stateKind}/${encodeURIComponent(name)}/state`, { method: "POST", body: fd });
      toast(`${name} → ${btn.dataset.state}`, "ok");
      refresh();
    }
    if (act === "delete") {
      confirmDialog(`Move "${btn.dataset.path}" to trash? It goes to ~/.claude/.trash/ and can be restored.`, async () => {
        await api(`/api/${kind}/${encodeURIComponent(base)}`, { method: "DELETE" });
        toast(`Trashed ${btn.dataset.path}`, "ok", {
          action: "undo",
          handler: async () => {
            await api(`/api/trash/restore/${kind}/${encodeURIComponent(base)}`, { method: "POST" });
            toast(`Restored ${btn.dataset.path}`, "ok");
            refresh();
          }
        });
        refresh();
      });
      return;
    }
    if (act === "edit") openEditModal(kind, base);
    if (act === "validate") {
      const res = await api(`/api/${kind}/${encodeURIComponent(base)}/validate`);
      showValidation(res, name);
    }
  } catch (err) {
    toast(err.message, "error");
  }
});

// Keyboard: Enter/Space on card name opens preview
grid.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    const nameEl = e.target.closest(".card-name");
    if (!nameEl) return;
    e.preventDefault();
    const card = nameEl.closest(".card");
    if (card?.dataset.kind && card?.dataset.base) {
      openPreview(card.dataset.kind, card.dataset.base);
    }
  }
});

// --- Preview modal ---

const previewModal = $("preview-modal");
let previewing = null;

async function openPreview(kind, base) {
  previewing = { kind, base };
  try {
    const d = await api(`/api/${kind}/${encodeURIComponent(base)}/preview`);
    $("preview-title-h").textContent = d.name;
    $("preview-desc").textContent = d.description || "";
    $("preview-tags").innerHTML = (d.tags || [])
      .map((t) => `<span class="tag-pill">${escapeHtml(t)}</span>`).join("");
    $("preview-path").textContent = d.path + (d.meta_file ? ` · ${d.meta_file}` : "");
    $("preview-content").innerHTML = renderMarkdown(d.body);

    // File listing for skill folders
    if (d.files && d.files.length) {
      $("preview-files-wrap").hidden = false;
      $("preview-files").innerHTML = d.files.map((f) =>
        `<div class="file-row"><span>${escapeHtml(f.path)}</span><span>${formatBytes(f.size)}</span></div>`
      ).join("");
    } else {
      $("preview-files-wrap").hidden = true;
    }

    // Show edit button only if editable (markdown has body)
    $("preview-edit").style.display = d.body !== "" ? "" : "none";

    previewModal.hidden = false;
    $("preview-close").focus();
  } catch (e) {
    toast(e.message, "error");
  }
}

$("preview-close").addEventListener("click", () => { previewModal.hidden = true; previewing = null; });
$("preview-edit").addEventListener("click", () => {
  if (!previewing) return;
  previewModal.hidden = true;
  openEditModal(previewing.kind, previewing.base);
});

// Escape key closes all modals
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  for (const id of ["preview-modal", "edit-modal", "bulk-modal", "create-modal", "trash-modal", "confirm-modal"]) {
    const m = $(id);
    if (m && !m.hidden) { m.hidden = true; return; }
  }
});

// --- Edit modal ---

const editModal = $("edit-modal");
let editing = null;

async function openEditModal(kind, base) {
  editing = { kind, base };
  try {
    const d = await api(`/api/${kind}/${encodeURIComponent(base)}/file`);
    $("edit-title-h").textContent = `Edit · ${base}`;
    $("edit-name").value = d.frontmatter.name || base;
    $("edit-desc").value = d.frontmatter.description || "";
    const tags = d.frontmatter.tags || d.frontmatter.categories || [];
    $("edit-tags").value = Array.isArray(tags) ? tags.join(", ") : tags;
    $("edit-body").value = d.body || "";
    $("edit-issues").innerHTML = "";
    // Tag autocomplete
    populateTagDatalist("edit-tags", "edit-tags-list");
    editModal.hidden = false;
    $("edit-name").focus();
  } catch (e) {
    toast(e.message, "error");
  }
}

$("edit-close").addEventListener("click", () => { editModal.hidden = true; editing = null; });

$("edit-save").addEventListener("click", async () => {
  if (!editing) return;
  const fm = {
    name: $("edit-name").value.trim(),
    description: $("edit-desc").value.trim(),
  };
  const tags = $("edit-tags").value.split(",").map((s) => s.trim()).filter(Boolean);
  if (tags.length) fm.tags = tags;
  try {
    await api(`/api/${editing.kind}/${encodeURIComponent(editing.base)}/file`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frontmatter: fm, body: $("edit-body").value }),
    });
    toast(`Saved ${editing.base}`, "ok");
    editModal.hidden = true;
    editing = null;
    refresh();
  } catch (e) {
    toast(e.message, "error");
  }
});

$("edit-validate").addEventListener("click", async () => {
  if (!editing) return;
  try {
    const res = await api(`/api/${editing.kind}/${encodeURIComponent(editing.base)}/validate`);
    showValidationInline(res);
  } catch (e) {
    toast(e.message, "error");
  }
});

function showValidationInline(res) {
  const el = $("edit-issues");
  if (res.issues.length === 0) {
    el.innerHTML = '<div class="issue info">No issues found.</div>';
    return;
  }
  el.innerHTML = res.issues.map((i) =>
    `<div class="issue ${i.level}">[${i.level}] ${escapeHtml(i.message)}</div>`).join("");
}

function showValidation(res, name) {
  if (res.issues.length === 0) {
    toast(`${name}: clean ✓`, "ok");
    return;
  }
  const errs = res.issues.filter((i) => i.level === "error").length;
  const warns = res.issues.filter((i) => i.level === "warning").length;
  toast(`${name}: ${errs} error(s), ${warns} warning(s)`, errs ? "error" : "ok");
  console.log(`Validation for ${name}:`, res.issues);
}

// --- Upload / clone / bulk ---

zipUpload.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    await api(`/api/${state.kind}/upload`, { method: "POST", body: fd });
    toast(`Uploaded ${file.name}`, "ok");
    refresh();
  } catch (err) { toast(err.message, "error"); }
  zipUpload.value = "";
});

cloneBtn.addEventListener("click", async () => {
  const url = prompt("Git repo URL (must end in .git):", "https://github.com/owner/repo.git");
  if (!url) return;
  const fd = new FormData();
  fd.append("url", url);
  try {
    await api(`/api/${state.kind}/clone`, { method: "POST", body: fd });
    toast(`Cloned into ${state.kind}/`, "ok");
    refresh();
  } catch (err) { toast(err.message, "error"); }
});

const bulkModal = $("bulk-modal");
bulkBtn.addEventListener("click", () => {
  $("bulk-url").value = "";
  $("bulk-subdir").value = "";
  $("bulk-result").innerHTML = "";
  bulkModal.hidden = false;
});
$("bulk-close").addEventListener("click", () => { bulkModal.hidden = true; });

$("bulk-go").addEventListener("click", async () => {
  const url = $("bulk-url").value.trim();
  const subdir = $("bulk-subdir").value.trim();
  if (!url) { toast("URL required", "error"); return; }
  $("bulk-result").innerHTML = '<div class="issue info">Cloning… this may take 30–60s.</div>';
  const fd = new FormData();
  fd.append("url", url);
  if (subdir) fd.append("subdir", subdir);
  try {
    const res = await api(`/api/${state.kind}/bulk-import`, { method: "POST", body: fd });
    $("bulk-result").innerHTML = `
      <div class="issue info">Imported ${res.imported.length}: ${res.imported.join(", ") || "(none)"}</div>
      <div class="issue warning">Skipped ${res.skipped.length}: ${res.skipped.join(", ") || "(none)"}</div>`;
    toast(`Imported ${res.imported.length} ${state.kind}`, "ok");
    refresh();
  } catch (e) {
    $("bulk-result").innerHTML = `<div class="issue error">${escapeHtml(e.message)}</div>`;
  }
});

// --- Create new asset ---

const createModal = $("create-modal");
const createBtn = $("create-btn");

createBtn.addEventListener("click", () => {
  $("create-name").value = "";
  $("create-desc").value = "";
  $("create-tags").value = "";
  $("create-result").innerHTML = "";
  populateTagDatalist("create-tags", "create-tags-list");
  createModal.hidden = false;
  $("create-name").focus();
});
$("create-close").addEventListener("click", () => { createModal.hidden = true; });

$("create-go").addEventListener("click", async () => {
  const name = $("create-name").value.trim();
  const desc = $("create-desc").value.trim();
  const tags = $("create-tags").value.trim();
  if (!name) { toast("Name is required", "error"); return; }
  const fd = new FormData();
  fd.append("name", name);
  fd.append("description", desc);
  fd.append("tags", tags);
  try {
    await api(`/api/${state.kind}/create`, { method: "POST", body: fd });
    toast(`Created ${state.kind}/${name}`, "ok");
    createModal.hidden = true;
    refresh();
  } catch (e) {
    $("create-result").innerHTML = `<div class="issue error">${escapeHtml(e.message)}</div>`;
  }
});

// --- Theme toggle ---

(function initTheme() {
  const saved = localStorage.getItem("cc-theme");
  if (saved) document.documentElement.dataset.theme = saved;
  if (themeToggle) {
    themeToggle.textContent = saved === "light" ? "dark" : "light";
  }
})();

if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme;
    const next = current === "light" ? "" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("cc-theme", next);
    themeToggle.textContent = next ? "dark" : "light";
  });
}

// --- Sort ---

if (sortSelect) {
  sortSelect.addEventListener("change", () => {
    const [by, dir] = sortSelect.value.split("-");
    state.sortBy = by;
    state.sortDir = dir === "asc" ? 1 : -1;
    renderGrid();
  });
}

// --- Keyboard shortcuts ---

document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "r") {
    e.preventDefault();
    refreshOnce("manual");
  }
});

// --- Confirmation dialog ---

function confirmDialog(message, onConfirm) {
  $("confirm-message").textContent = message;
  $("confirm-modal").hidden = false;
  $("confirm-yes").focus();
  $("confirm-yes").onclick = () => {
    $("confirm-modal").hidden = true;
    onConfirm();
  };
  $("confirm-no").onclick = () => { $("confirm-modal").hidden = true; };
}

// --- Trash management ---

const trashModal = $("trash-modal");

async function openTrash() {
  try {
    const items = await api("/api/trash");
    if (items.length === 0) {
      $("trash-list").innerHTML = '<div class="empty" style="padding:2rem;">trash is empty</div>';
    } else {
      const rows = items.map((it) => `
        <tr>
          <td><strong>${escapeHtml(it.name)}</strong></td>
          <td>${escapeHtml(it.kind)}</td>
          <td>${formatBytes(it.size)}</td>
          <td>${formatDate(it.trashed_at)}</td>
          <td>
            <button class="btn" data-trash-act="restore" data-kind="${escapeAttr(it.kind)}" data-name="${escapeAttr(it.name)}">restore</button>
            <button class="btn danger" data-trash-act="delete" data-kind="${escapeAttr(it.kind)}" data-name="${escapeAttr(it.name)}">delete forever</button>
          </td>
        </tr>
      `).join("");
      $("trash-list").innerHTML = `
        <table class="trash-table">
          <thead><tr><th>Name</th><th>Kind</th><th>Size</th><th>Trashed</th><th>Actions</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>`;
    }
    trashModal.hidden = false;
    $("trash-close").focus();
  } catch (e) {
    toast(e.message, "error");
  }
}

if (trashBtn) {
  trashBtn.addEventListener("click", openTrash);
}

$("trash-close").addEventListener("click", () => { trashModal.hidden = true; });

$("trash-list").addEventListener("click", async (e) => {
  const btn = e.target.closest("button[data-trash-act]");
  if (!btn) return;
  const { trashAct, kind, name } = btn.dataset;
  try {
    if (trashAct === "restore") {
      await api(`/api/trash/restore/${kind}/${encodeURIComponent(name)}`, { method: "POST" });
      toast(`Restored ${name}`, "ok");
    } else {
      confirmDialog(`Permanently delete "${name}"? This cannot be undone.`, async () => {
        await api(`/api/trash/${kind}/${encodeURIComponent(name)}`, { method: "DELETE" });
        toast(`Permanently deleted ${name}`, "ok");
        openTrash();
      });
      return;
    }
    openTrash();
    refresh();
  } catch (e) {
    toast(e.message, "error");
  }
});

// --- Auto-refresh (manual button + window focus / tab visibility) ---

let refreshing = false;
async function refreshOnce(source) {
  if (refreshing) return;
  refreshing = true;
  if (refreshBtn) refreshBtn.disabled = true;
  try {
    await refresh();
    if (source === "manual") toast("refreshed", "ok");
  } finally {
    refreshing = false;
    if (refreshBtn) refreshBtn.disabled = false;
  }
}

if (refreshBtn) {
  refreshBtn.addEventListener("click", () => refreshOnce("manual"));
}

// Re-scan when the user returns to the tab/window (clicking the app icon
// while the dashboard is already open counts as a focus event).
window.addEventListener("focus", () => refreshOnce("focus"));
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refreshOnce("visibility");
});

// --- Toast ---
function toast(msg, kind = "", opts = {}) {
  const t = document.createElement("div");
  t.className = "toast" + (kind ? " " + kind : "");
  t.setAttribute("role", "status");
  t.setAttribute("aria-live", "polite");
  t.textContent = msg;
  if (opts.action) {
    const btn = document.createElement("button");
    btn.className = "btn ghost";
    btn.textContent = opts.action;
    btn.style.marginLeft = "0.75rem";
    btn.addEventListener("click", () => { opts.handler(); t.remove(); });
    t.appendChild(btn);
  }
  document.body.appendChild(t);
  setTimeout(() => t.remove(), opts.action ? 6000 : 3500);
}

refresh();

// Realm Installer Deploy Dashboard
// Vanilla ES module. @dfinity/* loaded from esm.sh CDN. No build step.

let HttpAgent, Actor;

// ---- Configuration --------------------------------------------------

const DEFAULT_INSTALLER = "joj52-zaaaa-aaaah-qrejq-cai";
const params = new URLSearchParams(location.search);
const INSTALLER_ID = params.get("canister") || DEFAULT_INSTALLER;

const isLocal = location.hostname === "localhost"
  || location.hostname.endsWith(".localhost")
  || location.hostname === "127.0.0.1";

const HOST = isLocal
  ? `http://${location.hostname}:${location.port || "4943"}`
  : "https://icp0.io";

// ---- Candid IDL (inline) -------------------------------------------

const idlFactory = ({ IDL }) => {
  return IDL.Service({
    list_deploys: IDL.Func([], [IDL.Text], ["query"]),
    get_deploy_status: IDL.Func([IDL.Text], [IDL.Text], ["query"]),
    health: IDL.Func([], [IDL.Text], ["query"]),
  });
};

// ---- State ----------------------------------------------------------

let agent = null;
let actor = null;
let deploys = [];
let expandedTaskId = null;
let detailCache = {};
let refreshInterval = null;

const REFRESH_MS = 10000;

// ---- Boot -----------------------------------------------------------

async function boot() {
  try {
    const mod = await import("https://esm.sh/@dfinity/agent@2.1.3");
    HttpAgent = mod.HttpAgent;
    Actor = mod.Actor;

    agent = await HttpAgent.create({ host: HOST });
    if (isLocal) {
      try { await agent.fetchRootKey(); } catch {}
    }
    actor = Actor.createActor(idlFactory, { agent, canisterId: INSTALLER_ID });

    await refresh();
    refreshInterval = setInterval(refresh, REFRESH_MS);
  } catch (e) {
    showError(`Failed to connect: ${e.message}`);
  }
}

// ---- Data fetching --------------------------------------------------

async function refresh() {
  try {
    const raw = await actor.list_deploys();
    const data = JSON.parse(raw);
    if (!data.success) {
      showError(data.error || "list_deploys failed");
      return;
    }
    deploys = data.tasks || [];
    hideError();
    render();
    document.getElementById("last-refresh").textContent =
      `Updated ${new Date().toLocaleTimeString()}`;
  } catch (e) {
    showError(`Refresh failed: ${e.message}`);
  }
}

async function fetchDetail(taskId) {
  try {
    const raw = await actor.get_deploy_status(taskId);
    const data = JSON.parse(raw);
    if (!data.success) return null;
    detailCache[taskId] = data;
    return data;
  } catch {
    return null;
  }
}

// ---- Rendering ------------------------------------------------------

function render() {
  renderStats();
  renderTable();
}

function renderStats() {
  const total = deploys.length;
  const running = deploys.filter(d => d.status === "running").length;
  const queued = deploys.filter(d => d.status === "queued").length;
  const waiting = deploys.filter(d => d.status === "waiting").length;
  const failed = deploys.filter(d => d.status === "failed" || d.status === "partial").length;

  document.getElementById("stats").innerHTML = `
    <div class="stat"><div class="stat-value">${total}</div><div class="stat-label">Total</div></div>
    <div class="stat"><div class="stat-value">${running}</div><div class="stat-label">Running</div></div>
    <div class="stat"><div class="stat-value">${queued + waiting}</div><div class="stat-label">Queued</div></div>
    <div class="stat"><div class="stat-value">${failed}</div><div class="stat-label">Failed</div></div>
  `;
}

function renderTable() {
  if (deploys.length === 0) {
    document.getElementById("content").innerHTML =
      '<div class="empty">No deployments found.</div>';
    return;
  }

  let html = `<table>
    <thead><tr>
      <th>Task ID</th>
      <th>Status</th>
      <th>Target</th>
      <th class="hide-mobile">Steps</th>
      <th class="hide-mobile">Started</th>
      <th class="hide-mobile">Duration</th>
    </tr></thead><tbody>`;

  for (const d of deploys) {
    const isExpanded = d.task_id === expandedTaskId;
    html += `<tr data-id="${esc(d.task_id)}" class="${isExpanded ? "expanded" : ""}">
      <td class="mono">${esc(d.task_id)}</td>
      <td>${badge(d.status)}</td>
      <td class="mono">${shortPrincipal(d.target_canister_id)}</td>
      <td class="hide-mobile">${d.steps_count || 0}</td>
      <td class="hide-mobile">${formatTime(d.started_at)}</td>
      <td class="hide-mobile">${formatDuration(d.started_at, d.completed_at)}</td>
    </tr>`;

    if (isExpanded) {
      html += `<tr class="detail-row"><td colspan="6">${renderDetail(d.task_id)}</td></tr>`;
    }
  }

  html += "</tbody></table>";
  document.getElementById("content").innerHTML = html;

  document.querySelectorAll("tbody tr[data-id]").forEach(row => {
    row.addEventListener("click", () => toggleDetail(row.dataset.id));
  });
}

function renderDetail(taskId) {
  const detail = detailCache[taskId];
  if (!detail) return '<div class="detail-panel"><div class="loading">Loading steps...</div></div>';

  const steps = [];
  if (detail.wasm) steps.push(detail.wasm);
  if (detail.extensions) steps.push(...detail.extensions);
  if (detail.codices) steps.push(...detail.codices);

  if (steps.length === 0) {
    return '<div class="detail-panel"><div class="empty">No steps.</div></div>';
  }

  let html = '<div class="detail-panel"><h3>Steps</h3><div class="step-list">';
  for (const s of steps) {
    html += `<div class="step-card">
      <span class="step-idx">#${s.idx}</span>
      <div class="step-info">
        <div class="step-label">${esc(s.label || "unnamed")}</div>
        <div class="step-kind">${esc(s.kind || "")}</div>
        ${s.error ? `<div class="step-error">${esc(s.error)}</div>` : ""}
      </div>
      <div>
        ${badge(s.status)}
        <div class="step-timing">${formatDuration(s.started_at, s.completed_at)}</div>
      </div>
    </div>`;
  }
  html += "</div></div>";

  if (detail.error) {
    html = `<div class="detail-panel">
      <div class="step-error" style="margin-bottom:12px">Task error: ${esc(detail.error)}</div>
    </div>` + html;
  }

  return html;
}

// ---- Interactions ---------------------------------------------------

async function toggleDetail(taskId) {
  if (expandedTaskId === taskId) {
    expandedTaskId = null;
    renderTable();
    return;
  }
  expandedTaskId = taskId;
  renderTable();
  if (!detailCache[taskId]) {
    await fetchDetail(taskId);
    renderTable();
  }
}

// ---- Helpers --------------------------------------------------------

function badge(status) {
  const s = status || "unknown";
  return `<span class="badge badge-${s}">${s}</span>`;
}

function shortPrincipal(p) {
  if (!p) return "-";
  if (p.length <= 15) return esc(p);
  return esc(p.slice(0, 7) + "..." + p.slice(-5));
}

function formatTime(ts) {
  if (!ts) return "-";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" })
    + " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function formatDuration(start, end) {
  if (!start) return "-";
  const finish = end || Math.floor(Date.now() / 1000);
  const secs = finish - start;
  if (secs < 0) return "-";
  if (secs < 60) return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
}

function esc(s) {
  if (!s) return "";
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showError(msg) {
  const el = document.getElementById("error-banner");
  el.textContent = msg;
  el.style.display = "block";
}

function hideError() {
  document.getElementById("error-banner").style.display = "none";
}

// ---- Start ----------------------------------------------------------
boot();

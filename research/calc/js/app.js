import {
  loadBaseline,
  readStatsFromForm,
  scoreAllTeams,
  buildReportAll,
  applyPreset,
} from "./engine.js";
import {
  renderOverviewAcademic,
  renderOverviewCoach,
  renderTeamAcademic,
  renderTeamCoach,
  verdictClass,
} from "./views.js";

const STAT_LABELS = {
  "p36_PPG": "p36 PPG",
  "p36_APG": "p36 APG",
  "p36_RPG": "p36 RPG",
  "p36_3PA": "p36 3PA",
  "p36_SPG": "p36 SPG",
  "p36_BPG": "p36 BPG",
  "adv_USG%": "USG% (0~1)",
  "adv_AST%": "AST% (0~1)",
  "adv_TRB%": "TRB% (0~1)",
  "adv_STL%": "STL% (0~1)",
  "adv_BLK%": "BLK% (0~1)",
};

const TABS = [
  { id: "overview", label: "종합" },
  { id: "LIN", label: "브렉스" },
  { id: "AIS", label: "미카와" },
  { id: "CCT", label: "군마" },
];

const mounts = new WeakMap();

function buildStatInputs(root, fields) {
  const grid = root.querySelector("#statGrid");
  grid.innerHTML = "";
  for (const f of fields) {
    const wrap = document.createElement("label");
    wrap.className = "field";
    wrap.innerHTML = `<span>${STAT_LABELS[f] || f}</span><input type="number" step="any" id="${f}" />`;
    grid.appendChild(wrap);
  }
}

function setMode(root, mode) {
  const m = mounts.get(root);
  m.state.mode = mode;
  root.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  renderOutput(root);
}

function setTab(root, tab) {
  const m = mounts.get(root);
  m.state.tab = tab;
  root.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  renderOutput(root);
}

function updateNavBadges(root, results) {
  for (const r of results) {
    const btn = root.querySelector(`[data-tab="${r.benchCode}"]`);
    if (!btn) continue;
    let badge = btn.querySelector(".tab-verdict");
    if (!badge) {
      badge = document.createElement("span");
      badge.className = "tab-verdict";
      btn.appendChild(badge);
    }
    badge.textContent = r.verdict.split(" ")[0];
    badge.className = `tab-verdict ${verdictClass(r.verdict)}`;
  }
}

function renderOutput(root) {
  const m = mounts.get(root);
  if (!m?.baseline || !m.lastResults.length) return;

  const mount = root.querySelector("#resultView");
  const { mode, tab } = m.state;
  const { name, mpg } = m.lastInput;

  if (tab === "overview") {
    mount.innerHTML =
      mode === "academic"
        ? renderOverviewAcademic(m.lastResults, m.baseline, name, mpg)
        : renderOverviewCoach(m.lastResults, m.baseline, name, mpg);
    return;
  }

  const r = m.lastResults.find((x) => x.benchCode === tab);
  const meta = m.baseline.teamMeta[tab];
  if (!r || !meta) {
    mount.innerHTML = "<p class='muted'>데이터 없음</p>";
    return;
  }

  mount.innerHTML =
    mode === "academic"
      ? renderTeamAcademic(r, meta, m.baseline)
      : renderTeamCoach(r, meta, m.baseline);
}

function runCalc(root) {
  const m = mounts.get(root);
  if (!m?.baseline) return;
  const { stats, name, mpg } = readStatsFromForm(m.baseline.statFields, root);
  m.lastInput = { name, mpg };
  m.lastResults = scoreAllTeams(stats, name, mpg, m.baseline);
  updateNavBadges(root, m.lastResults);

  const brex = m.lastResults.find((x) => x.benchCode === "LIN");
  const best = [...m.lastResults].sort((a, b) => a.wAfter - b.wAfter)[0];
  const badge = root.querySelector("#verdictBadge");
  if (badge && brex && best) {
    badge.textContent = `브렉스 ${brex.verdict} · 가장 유사 ${best.benchShort} W=${best.wAfter}`;
    badge.className = `badge ${verdictClass(brex.verdict)}`;
  }

  root.querySelector("#reportMd").textContent = buildReportAll(m.lastResults, m.baseline);
  renderOutput(root);
}

function buildNav(root) {
  const nav = root.querySelector("#resultNav");
  nav.innerHTML = TABS.map(
    (t) => `<button type="button" class="nav-tab" data-tab="${t.id}">${t.label}</button>`,
  ).join("");
  nav.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => setTab(root, btn.dataset.tab));
  });
}

function bindCalcEvents(root) {
  const m = mounts.get(root);
  const run = () => runCalc(root);

  root.querySelector("#btnCalc").addEventListener("click", run);
  root.querySelector("#btnPresetLayman").addEventListener("click", () => {
    applyPreset(m.baseline, "layman", root);
    run();
  });
  root.querySelector("#btnPresetWoodbury").addEventListener("click", () => {
    applyPreset(m.baseline, "woodbury", root);
    run();
  });

  root.querySelectorAll("[data-mode]").forEach((btn) => {
    btn.addEventListener("click", () => setMode(root, btn.dataset.mode));
  });

  root.querySelector("#btnCopy").addEventListener("click", () => {
    navigator.clipboard.writeText(root.querySelector("#reportMd").textContent);
  });
  root.querySelector("#btnDownload").addEventListener("click", () => {
    const t = root.querySelector("#reportMd").textContent;
    const blob = new Blob([t], { type: "text/markdown;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "2번째_용병_슬롯_3팀결과.md";
    a.click();
  });

  ["expectedMpg", "candidateName", ...m.baseline.statFields].forEach((id) => {
    const el = root.querySelector(`#${id}`);
    if (el) el.addEventListener("input", run);
  });

  m.cleanup = run;
}

export async function initCalc(root, { baseline: baselineData } = {}) {
  if (!root) throw new Error("calc root element required");

  destroyCalc(root);

  const baseline = await loadBaseline(baselineData);
  mounts.set(root, {
    baseline,
    state: { mode: "coach", tab: "overview" },
    lastResults: [],
    lastInput: { name: "", mpg: 28 },
    cleanup: null,
  });

  buildStatInputs(root, baseline.statFields);
  buildNav(root);
  bindCalcEvents(root);

  applyPreset(baseline, baseline.defaultPreset || "layman", root);
  setMode(root, "coach");
  setTab(root, "overview");
  runCalc(root);
}

export function destroyCalc(root) {
  const m = mounts.get(root);
  if (!m) return;
  mounts.delete(root);
}

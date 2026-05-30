/**
 * 2번째 용병 슬롯 계산기 — Python second_import_slot.py 와 동일 수식
 */

const ROLES = ["scoring", "playmaking", "rebounding", "defense", "spacing"];
const BENCH_CODES = ["LIN", "AIS", "CCT"];

/** 1D Wasserstein — scipy.stats._cdf_distance(p=1) 와 동일 */
function wasserstein5(uWeights, vWeights) {
  const n = uWeights.length;
  const positions = Array.from({ length: n }, (_, i) => i);
  const uSum = uWeights.reduce((a, b) => a + b, 0) || 1;
  const vSum = vWeights.reduce((a, b) => a + b, 0) || 1;
  const u = uWeights.map((w) => w / uSum);
  const v = vWeights.map((w) => w / vSum);

  const allValues = positions.concat(positions).sort((a, b) => a - b);
  const uCum = [0];
  const vCum = [0];
  for (let i = 0; i < n; i++) {
    uCum.push(uCum[uCum.length - 1] + u[i]);
    vCum.push(vCum[vCum.length - 1] + v[i]);
  }

  let w = 0;
  for (let i = 0; i < allValues.length - 1; i++) {
    const x = allValues[i];
    const delta = allValues[i + 1] - x;
    if (delta === 0) continue;
    let ui = 0;
    while (ui < n && positions[ui] <= x) ui++;
    let vi = 0;
    while (vi < n && positions[vi] <= x) vi++;
    const uCdf = uCum[ui] / uCum[n];
    const vCdf = vCum[vi] / vCum[n];
    w += Math.abs(uCdf - vCdf) * delta;
  }
  return w;
}

function distFromRaw(raw) {
  const s = raw.reduce((x, y) => x + y, 0);
  return raw.map((v) => v / (s + 1e-9));
}

function teamW(baseRaw, mpg, importV, target) {
  const combined = baseRaw.map((v, i) => v + mpg * importV[i]);
  const d = distFromRaw(combined);
  return wasserstein5(target, d);
}

function roleLoadVector(stats, roleLoadCols) {
  const out = [];
  for (const role of ROLES) {
    const cols = roleLoadCols[role];
    const vals = cols
      .filter((c) => stats[c] != null && !Number.isNaN(stats[c]))
      .map((c) => Number(stats[c]));
    out.push(vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0);
  }
  return out;
}

function normalizePctField(name, val) {
  let v = Number(val);
  if (Number.isNaN(v)) return 0;
  if (name.startsWith("adv_") && v > 1.5) v = v / 100;
  return v;
}

function readStatsFromForm(fields, root) {
  const stats = {};
  for (const f of fields) {
    const el = root.querySelector(`#${f}`);
    stats[f] = normalizePctField(f, el?.value ?? 0);
  }
  const name = root.querySelector("#candidateName")?.value?.trim() || "후보";
  const mpg = Number(root.querySelector("#expectedMpg")?.value ?? 28);
  return { stats, name, mpg };
}

function mpgSlotKey(mpg) {
  return String(Math.round(Math.max(18, Math.min(36, mpg))));
}

function getSlot(baseline, benchCode, mpg) {
  const key = mpgSlotKey(mpg);
  const slot = baseline.idealsByMpg[key]?.[benchCode];
  if (!slot) {
    throw new Error(`MPG ${key} 데이터 없음. export_baseline.py 재실행.`);
  }
  return slot;
}

function scoreCandidate(stats, name, mpg, baseline, benchCode) {
  const slot = getSlot(baseline, benchCode, mpg);
  const target = baseline.targets[benchCode];
  const ideal = slot.ideal;
  const importV = roleLoadVector(stats, baseline.roleLoadCols);
  const wAfter = teamW(baseline.baseRaw, mpg, importV, target);
  const wOne = slot.wOne;
  const wOpt = slot.wOptimal;
  const improve = ((wOne - wAfter) / (wOne + 1e-9)) * 100;
  const deltaOpt = Math.abs(wAfter - wOpt);

  const roleGaps = {};
  const needMore = [];
  const needLess = [];
  ROLES.forEach((r, i) => {
    const g = ideal[i] - importV[i];
    roleGaps[r] = Math.round(g * 1000) / 1000;
    if (g > 0.05) needMore.push(r);
    if (g < -0.05) needLess.push(r);
  });

  let verdict;
  if (wAfter <= wOpt + 0.005) verdict = "매우 유사";
  else if (improve >= 25) verdict = "유사";
  else if (improve >= 10) verdict = "다소 유사";
  else if (improve > 0) verdict = "거리 있음";
  else verdict = "상이";

  const coaching = [
    ...needMore.map((r) => `↑ ${baseline.roleCoachHint[r]}`),
    ...needLess.map((r) => `↓ ${baseline.roleCoachHint[r]}`),
  ];

  const meta = baseline.teamMeta?.[benchCode] ?? { short: benchCode, label: benchCode };

  return {
    name,
    mpg,
    benchCode,
    benchLabel: meta.label ?? benchCode,
    benchShort: meta.short ?? benchCode,
    importV,
    wOne,
    wOpt,
    wAfter: Math.round(wAfter * 10000) / 10000,
    improvePct: Math.round(improve * 10) / 10,
    deltaOpt: Math.round(deltaOpt * 10000) / 10000,
    verdict,
    roleGaps,
    teamGapOne: slot.teamGapOne,
    ideal: Object.fromEntries(ROLES.map((r, i) => [r, Math.round(ideal[i] * 1000) / 1000])),
    coaching,
  };
}

function scoreAllTeams(stats, name, mpg, baseline) {
  return BENCH_CODES.map((code) => scoreCandidate(stats, name, mpg, baseline, code));
}

function buildReportAll(allResults, baseline) {
  const { name, mpg } = allResults[0] ?? { name: "후보", mpg: 28 };
  const lines = [
    "# 2번째 용병 슬롯 — 3팀 계산 결과",
    "",
    `> 후보: **${name}** · MPG **${mpg}** · 브라우저 로컬 계산`,
    "",
    "## 3팀 요약",
    "",
    "| 벤치마크 | W_one | W_opt | W_after | vs 1빅 | 유사도 |",
    "|----------|:-----:|:-----:|:-------:|:------:|:----:|",
  ];
  for (const r of allResults) {
    lines.push(
      `| ${r.benchShort} | ${r.wOne} | ${r.wOpt} | ${r.wAfter} | ${r.improvePct >= 0 ? "+" : ""}${r.improvePct}% | ${r.verdict} |`,
    );
  }
  for (const r of allResults) {
    lines.push("", `## ${r.benchLabel}`, "", buildReport(r, baseline));
  }
  return lines.join("\n");
}

function buildReport(result, baseline) {
  const lines = [
    "### 요약",
    "",
    "| 항목 | 값 |",
    "|------|-----|",
    `| 1빅 Role W | **${result.wOne}** |`,
    `| 역산 기준 W | **${result.wOpt}** |`,
    `| 후보 W | **${result.wAfter}** |`,
    `| vs 1빅 | **${result.improvePct >= 0 ? "+" : ""}${result.improvePct}%** |`,
    `| **유사도** | **${result.verdict}** |`,
    "",
    "### ideal vs 후보",
    "",
    "| role | 이상 | 후보 | gap |",
    "|------|:----:|:----:|:---:|",
  ];
  ROLES.forEach((r, i) => {
    const iv = Math.round(result.importV[i] * 1000) / 1000;
    const g = result.roleGaps[r];
    lines.push(`| ${r} | ${result.ideal[r]} | ${iv} | ${g >= 0 ? "+" : ""}${g} |`);
  });
  if (result.coaching.length) {
    lines.push("", "### 코칭", "");
    result.coaching.forEach((c) => lines.push(`- ${c}`));
  }
  return lines.join("\n");
}

async function loadBaseline(preloaded) {
  if (preloaded) return preloaded;
  if (typeof window !== "undefined" && window.BASELINE) return window.BASELINE;
  const res = await fetch("data/baseline.json");
  if (!res.ok) throw new Error("baseline 로드 실패 — export_baseline.py 실행");
  return res.json();
}

function fillFormFromCandidate(candidate, statFields, root) {
  root.querySelector("#candidateName").value = candidate.name;
  root.querySelector("#expectedMpg").value = candidate.avg_MPG ?? 28;
  for (const f of statFields) {
    const el = root.querySelector(`#${f}`);
    if (el && candidate[f] != null) el.value = candidate[f];
  }
}

function applyPreset(baseline, presetId, root) {
  const cand = baseline.presets?.[presetId];
  if (!cand) return;
  fillFormFromCandidate(cand, baseline.statFields, root);
}

export {
  loadBaseline,
  readStatsFromForm,
  scoreCandidate,
  scoreAllTeams,
  buildReport,
  buildReportAll,
  fillFormFromCandidate,
  applyPreset,
  mpgSlotKey,
};

/** HTML 결과 뷰 — 학회용 / 구단용 */

const ROLE_KO = {
  scoring: "득점",
  playmaking: "볼분배",
  rebounding: "리바운드",
  defense: "디펜스",
  spacing: "spacing(3P)",
};

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function verdictClass(v) {
  if (v.includes("매우 유사") || v === "유사") return "good";
  if (v.includes("다소 유사") || v.includes("거리")) return "mid";
  return "bad";
}

function coachVerdictLine(r, meta) {
  const imp = r.improvePct;
  const lines = [
    `<strong>${esc(r.name)}</strong> · ${meta.short} 기준 · 예상 ${r.mpg}분`,
  ];
  if (r.verdict === "매우 유사") {
    lines.push(`W ${r.wAfter} — 역산 기준(W ${r.wOpt})에 거의 닿음. 벤치마크 전술 분포와 <strong>매우 유사</strong>.`);
  } else if (r.verdict === "유사") {
    lines.push(`1빅 대비 W ${imp >= 0 ? "+" : ""}${imp}% — 벤치마크와 <strong>유사</strong>한 방향.`);
  } else if (r.verdict === "다소 유사") {
    lines.push(`W는 줄었으나(${imp >= 0 ? "+" : ""}${imp}%) 벤치마크와 <strong>다소 유사</strong> — stat·MPG 재검토.`);
  } else if (r.verdict === "거리 있음") {
    lines.push(`W 변화가 작음(${imp >= 0 ? "+" : ""}${imp}%) — ${meta.short} 그림과 <strong>거리 있음</strong>.`);
  } else {
    lines.push(`1빅보다 W가 커짐 — 벤치마크 전술 분포와 <strong>상이</strong>.`);
  }
  return lines.join(" ");
}

function gapHint(g, mode) {
  if (g > 0.05) return mode === "coach" ? "부족 → 2빅이 채울 역할" : "gap>0 · 벤치마크 대비 부족";
  if (g < -0.05) return mode === "coach" ? "과잉 → 줄이거나 다른 역할" : "gap<0 · 벤치마크 대비 과잉";
  return mode === "coach" ? "비슷" : "≈0 · 균형";
}

function metricCards(r) {
  return `
    <div class="metric-grid">
      <div class="metric"><span>1빅 W</span><strong>${r.wOne}</strong><em>W_one</em></div>
      <div class="metric"><span>역산 기준 W</span><strong>${r.wOpt}</strong><em>W_optimal</em></div>
      <div class="metric highlight"><span>후보 적용</span><strong>${r.wAfter}</strong><em>W_after</em></div>
      <div class="metric"><span>vs 1빅</span><strong>${r.improvePct >= 0 ? "+" : ""}${r.improvePct}%</strong><em>W 변화율</em></div>
      <div class="metric"><span>ideal ΔW</span><strong>${r.deltaOpt}</strong><em>|W−W_opt|</em></div>
    </div>`;
}

function roleBar(role, ideal, actual, gap) {
  const max = Math.max(ideal, actual, 0.01) * 1.15;
  const iw = (ideal / max) * 100;
  const aw = (actual / max) * 100;
  return `
    <div class="role-row">
      <div class="role-name">${ROLE_KO[role] || role}</div>
      <div class="role-bars">
        <div class="bar ideal" style="width:${iw}%"></div>
        <div class="bar actual" style="width:${aw}%"></div>
      </div>
      <div class="role-nums">
        <span class="ideal-n">이상 ${ideal}</span>
        <span class="act-n">후보 ${actual}</span>
        <span class="gap-n ${gap >= 0 ? "pos" : "neg"}">${gap >= 0 ? "+" : ""}${gap}</span>
      </div>
    </div>`;
}

function renderTeamAcademic(r, meta, baseline) {
  const roles = baseline.roles;
  const gapRows = roles
    .map(
      (role) => `<tr>
        <td>${ROLE_KO[role]}</td>
        <td class="num">${r.teamGapOne[role] >= 0 ? "+" : ""}${r.teamGapOne[role]}</td>
        <td>${gapHint(r.teamGapOne[role], "academic")}</td>
      </tr>`,
    )
    .join("");

  const idealRows = roles
    .map((role, i) => {
      const iv = Math.round(r.importV[i] * 1000) / 1000;
      const g = r.roleGaps[role];
      return `<tr>
        <td>${ROLE_KO[role]}</td>
        <td class="num">${r.ideal[role]}</td>
        <td class="num">${iv}</td>
        <td class="num ${g >= 0 ? "pos" : "neg"}">${g >= 0 ? "+" : ""}${g}</td>
        <td>${baseline.roleCoachHint[role]}</td>
      </tr>`;
    })
    .join("");

  const coachList = liveCoachingList(r);

  const roleBars = roles
    .map((role, i) =>
      roleBar(role, r.ideal[role], Math.round(r.importV[i] * 1000) / 1000, r.roleGaps[role]),
    )
    .join("");

  return `
    <section class="view-section">
      <div class="section-head">
        <h3>${esc(meta.label)} · ${esc(meta.rank)}</h3>
        <span class="badge ${verdictClass(r.verdict)}">${esc(r.verdict)}</span>
      </div>
      <p class="meta-line">${esc(meta.focus)} · film: ${esc(meta.film)}</p>
      ${metricCards(r)}
    </section>

    <section class="view-section">
      <h4>1.4 Role W 지표 (학술 정의)</h4>
      <div class="note-box">
        <p><strong>W</strong> = 5-bin Wasserstein(삼성 팀 role 분포, ${meta.short} target 분포). MPG 가중 합산 후 정규화.</p>
        <p><strong>역산 ideal</strong> = SLSQP로 W_optimal까지 2번째 슬롯 role vector 역산 (ML 없음).</p>
        <p><strong>유사도 구간</strong>: W_after≈W_opt → 매우 유사 | W↓≥25% → 유사 | ≥10% → 다소 유사 | &gt;0 → 거리 있음 | W↑ → 상이.</p>
      </div>
    </section>

    <section class="view-section">
      <h4>1빅 대비 팀 role gap (target − 현재 1빅)</h4>
      <table class="data-table">
        <thead><tr><th>role</th><th>gap</th><th>해석</th></tr></thead>
        <tbody>${gapRows}</tbody>
      </table>
    </section>

    <section class="view-section">
      <h4>역산 ideal vs 후보 role vector</h4>
      <div class="legend"><span class="dot ideal"></span>이상값 <span class="dot actual"></span>후보값</div>
      ${roleBars}
      <table class="data-table compact">
        <thead><tr><th>role</th><th>이상</th><th>후보</th><th>gap</th><th>stat 힌트</th></tr></thead>
        <tbody>${idealRows}</tbody>
      </table>
    </section>

    <section class="view-section">
      <h4>코칭 힌트 (ideal 대비 · 실시간)</h4>
      <p class="muted live-note">후보 stat·MPG 변경 시 자동 갱신.</p>
      ${coachList}
    </section>`;
}

function liveCoachingList(r, emptyMsg) {
  if (r.coaching.length) {
    return `<ul class="coach-list live-coach">${r.coaching.map((c) => `<li>${esc(c)}</li>`).join("")}</ul>`;
  }
  return `<p class="muted">${emptyMsg || "ideal 대비 ±0.05 이내 — 역할별 큰 조정 힌트 없음"}</p>`;
}

function liveRoleSummary(r) {
  const roles = ["scoring", "playmaking", "rebounding", "defense", "spacing"];
  const needMore = roles.filter((role) => r.roleGaps[role] > 0.05);
  const needLess = roles.filter((role) => r.roleGaps[role] < -0.05);
  const parts = [];
  if (needMore.length) parts.push(`↑ ${needMore.map((role) => ROLE_KO[role]).join(" · ")}`);
  if (needLess.length) parts.push(`↓ ${needLess.map((role) => ROLE_KO[role]).join(" · ")}`);
  return parts.length ? parts.join(" · ") : "역할 밸런스 OK";
}

function renderLiveCoachingBlock(r, baseline, mode) {
  const title = mode === "coach" ? "실시간 코칭 (ideal 대비)" : "Live coaching (ideal gap)";
  const note =
    mode === "coach"
      ? "후보 stat·MPG를 바꿀 때마다 갱신됩니다. ↑ = ideal보다 부족 · ↓ = ideal보다 과함."
      : "Updates on every stat/MPG change. ↑ below ideal · ↓ above ideal.";

  const idealRows = baseline.roles
    .map((role, i) => {
      const iv = Math.round(r.importV[i] * 1000) / 1000;
      const g = r.roleGaps[role];
      return `<tr>
        <td>${ROLE_KO[role]}</td>
        <td class="num">${r.ideal[role]}</td>
        <td class="num">${iv}</td>
        <td class="num ${g >= 0 ? "pos" : "neg"}">${g >= 0 ? "+" : ""}${g}</td>
        <td>${baseline.roleCoachHint[role]}</td>
      </tr>`;
    })
    .join("");

  return `
    <section class="view-section live-coaching">
      <h4>${title}</h4>
      <p class="muted live-note">${note}</p>
      ${liveCoachingList(r)}
      <table class="data-table compact">
        <thead><tr><th>role</th><th>이상</th><th>후보</th><th>gap</th><th>stat 힌트</th></tr></thead>
        <tbody>${idealRows}</tbody>
      </table>
    </section>`;
}

function renderTeamCoach(r, meta, baseline) {
  const roles = ["scoring", "playmaking", "rebounding", "defense", "spacing"];
  const needMore = roles.filter((role) => r.roleGaps[role] > 0.05);
  const needLess = roles.filter((role) => r.roleGaps[role] < -0.05);

  const actionCards = [];
  if (needMore.length) {
    actionCards.push(
      `<div class="action-card up"><h5>더 필요한 역할</h5><p>${needMore.map((r) => ROLE_KO[r]).join(" · ")}</p></div>`,
    );
  }
  if (needLess.length) {
    actionCards.push(
      `<div class="action-card down"><h5>줄이거나 분담할 역할</h5><p>${needLess.map((r) => ROLE_KO[r]).join(" · ")}</p></div>`,
    );
  }
  if (!actionCards.length) {
    actionCards.push(`<div class="action-card ok"><h5>역할 밸런스</h5><p>이상 프로필과 큰 차이 없음</p></div>`);
  }

  return `
    <section class="view-section coach-hero">
      <div class="section-head">
        <h3>${esc(meta.short)} — ${esc(meta.rank)}</h3>
        <span class="badge ${verdictClass(r.verdict)}">${esc(r.verdict)}</span>
      </div>
      <p class="coach-lead">${coachVerdictLine(r, meta)}</p>
      ${metricCards(r)}
    </section>

    <section class="view-section">
      <h4>코트에서 읽으면</h4>
      <div class="coach-cards">${actionCards.join("")}</div>
      <p class="film-tip"><strong>film 참고:</strong> ${esc(meta.film)}</p>
      <p class="muted">${esc(meta.coachUse)}</p>
    </section>

    ${renderLiveCoachingBlock(r, baseline, "coach")}

    <section class="view-section">
      <h4>숫자 한눈에</h4>
      <table class="data-table coach-table">
        <tr><th>1빅만 (W)</th><td>${r.wOne}</td><th>후보 넣으면 (W)</th><td><strong>${r.wAfter}</strong></td></tr>
        <tr><th>역산 기준 (W)</th><td>${r.wOpt}</td><th>W 변화율</th><td>${r.improvePct >= 0 ? "+" : ""}${r.improvePct}%</td></tr>
      </table>
    </section>`;
}

function renderOverviewAcademic(allResults, baseline, name, mpg) {
  const sorted = [...allResults].sort((a, b) => a.wAfter - b.wAfter);
  const rows = allResults
    .map((r) => {
      const meta = baseline.teamMeta[r.benchCode];
      return `<tr>
        <td>${esc(meta.short)} (${r.benchCode})</td>
        <td class="num">${r.wOne}</td>
        <td class="num">${r.wOpt}</td>
        <td class="num"><strong>${r.wAfter}</strong></td>
        <td class="num">${r.improvePct >= 0 ? "+" : ""}${r.improvePct}%</td>
        <td><span class="badge sm ${verdictClass(r.verdict)}">${esc(r.verdict)}</span></td>
      </tr>`;
    })
    .join("");

  return `
    <section class="view-section">
      <h3>3팀 벤치마크 종합</h3>
      <p class="meta-line">후보 <strong>${esc(name)}</strong> · MPG <strong>${mpg}</strong> · 칸터+국내(1빅) baseline</p>
      <p class="rank-note">Role W <strong>낮을수록</strong> 해당 팀 전술 그림에 가깝습니다. 브렉스≈전술 1순위 · 미카와≈PF 로테 · 군마≈지형 진단.</p>
      <table class="data-table">
        <thead><tr><th>벤치마크</th><th>W_one</th><th>W_opt</th><th>W_after</th><th>vs 1빅</th><th>유사도</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <p class="muted">가장 가까운 팀: <strong>${esc(sorted[0] && baseline.teamMeta[sorted[0].benchCode].short)}</strong> (W=${sorted[0]?.wAfter})</p>
    </section>
    <section class="view-section">
      <h4>팀별 live coaching (ideal gap)</h4>
      <table class="data-table">
        <thead><tr><th>팀</th><th>↑/↓ roles</th><th>verdict</th></tr></thead>
        <tbody>${allResults
          .map((r) => {
            const meta = baseline.teamMeta[r.benchCode];
            return `<tr>
              <td>${esc(meta.short)}</td>
              <td>${esc(liveRoleSummary(r))}</td>
              <td>${esc(r.verdict)}</td>
            </tr>`;
          })
          .join("")}</tbody>
      </table>
    </section>
    <section class="view-section">
      <h4>방법론 (학회용)</h4>
      <div class="note-box">
        <p>본 계산기는 보고서 <code>second_import_slot.py</code> / 학술보완 MPG 가중 dual 시나리오와 <strong>동일 Role W 수식</strong>.</p>
        <p>bootstrap·FDR·9방법론은 별도 보고서 — 여기서는 <strong>2번째 슬롯 Role W 역산·채점</strong>만.</p>
      </div>
    </section>`;
}

function renderOverviewCoach(allResults, baseline, name, mpg) {
  const cards = allResults
    .map((r) => {
      const meta = baseline.teamMeta[r.benchCode];
      return `
        <article class="team-summary-card ${verdictClass(r.verdict)}">
          <header>
            <h4>${esc(meta.short)}</h4>
            <span class="badge sm ${verdictClass(r.verdict)}">${esc(r.verdict)}</span>
          </header>
          <p class="card-sub">${esc(meta.rank)}</p>
          <p>W ${r.wOne} → <strong>${r.wAfter}</strong> (${r.improvePct >= 0 ? "+" : ""}${r.improvePct}%)</p>
          <p class="card-use">${esc(meta.coachUse)}</p>
        </article>`;
    })
    .join("");

  const best = [...allResults].sort((a, b) => a.wAfter - b.wAfter)[0];
  const bestMeta = best ? baseline.teamMeta[best.benchCode] : null;

  return `
    <section class="view-section">
      <h3>3팀 한눈에</h3>
      <p class="coach-lead"><strong>${esc(name)}</strong> · ${mpg}분 가정 — 브렉스·미카와·군마 <strong>전부</strong> 같은 stat으로 계산.</p>
      <div class="team-summary-grid">${cards}</div>
      ${
        bestMeta
          ? `<div class="highlight-box">벤치마크와 가장 가까운 팀: <strong>${esc(bestMeta.short)}</strong> (W ${best.wAfter}) — ${esc(best.verdict)}</div>`
          : ""
      }
    </section>
    <section class="view-section">
      <h4>팀별 실시간 코칭 요약</h4>
      <p class="muted live-note">ideal role vector 대비 — stat 입력마다 바뀝니다.</p>
      <table class="data-table">
        <thead><tr><th>팀</th><th>역할 조정</th><th>유사도</th></tr></thead>
        <tbody>${allResults
          .map((r) => {
            const meta = baseline.teamMeta[r.benchCode];
            return `<tr>
              <td>${esc(meta.short)}</td>
              <td>${esc(liveRoleSummary(r))}</td>
              <td><span class="badge sm ${verdictClass(r.verdict)}">${esc(r.verdict)}</span></td>
            </tr>`;
          })
          .join("")}</tbody>
      </table>
    </section>`;
}

export {
  renderOverviewAcademic,
  renderOverviewCoach,
  renderTeamAcademic,
  renderTeamCoach,
  verdictClass,
};

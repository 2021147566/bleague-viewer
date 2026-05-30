import { useEffect, useRef } from "react";
import baselineData from "../research/calc/data/baseline.json";
import { initCalc, destroyCalc } from "../research/calc/js/app.js";
import "../research/calc/css/style.css";

export default function CalcPage() {
  const rootRef = useRef(null);

  useEffect(() => {
    const el = rootRef.current;
    if (!el) return undefined;
    initCalc(el, { baseline: baselineData }).catch((err) => {
      el.innerHTML = `<pre class="calc-error">${err.message}</pre>`;
    });
    return () => destroyCalc(el);
  }, []);

  return (
    <div className="calc-page">
      <div ref={rootRef} className="calc-app">
        <header className="calc-hero">
          <h1>2번째 용병 슬롯 계산</h1>
          <p>칸터+국내(1빅) · Role W 역산 · stat 입력마다 유사도·코칭 실시간 갱신</p>
        </header>

        <div className="layout">
          <section className="panel inputs">
            <h2>후보 입력</h2>
            <label className="field wide">
              <span>선수명</span>
              <input type="text" id="candidateName" />
            </label>
            <label className="field">
              <span>예상 MPG (18~36)</span>
              <input type="number" id="expectedMpg" min="18" max="36" step="0.1" value="27" />
            </label>

            <h3>프리셋</h3>
            <div className="preset-row">
              <button type="button" id="btnPresetLayman" className="preset">
                제이크 레이맨
              </button>
              <button type="button" id="btnPresetWoodbury" className="preset">
                우드버리 (placeholder)
              </button>
            </div>

            <h3>Role Load stat</h3>
            <div id="statGrid" className="stat-grid" />

            <div className="actions">
              <button type="button" id="btnCalc" className="primary">
                재계산
              </button>
            </div>
          </section>

          <section className="panel output">
            <div className="output-toolbar">
              <div className="mode-switch">
                <span className="toolbar-label">보기 모드</span>
                <button type="button" className="mode-btn active" data-mode="coach">
                  구단용
                </button>
                <button type="button" className="mode-btn" data-mode="academic">
                  학회용
                </button>
              </div>
              <span id="verdictBadge" className="badge">
                —
              </span>
            </div>

            <nav id="resultNav" className="result-nav" aria-label="결과 섹션" />

            <div id="resultView" className="result-view" />

            <details className="md-export" id="mdPanel">
              <summary>Markdown 내보내기 (접기)</summary>
              <div className="report-actions">
                <button type="button" id="btnCopy">
                  복사
                </button>
                <button type="button" id="btnDownload">
                  .md 저장
                </button>
              </div>
              <pre id="reportMd" className="report-md" />
            </details>
          </section>
        </div>
      </div>
    </div>
  );
}

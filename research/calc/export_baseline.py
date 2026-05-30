#!/usr/bin/env python3
"""xlsx → calc/data/baseline.json (브라우저 계산기용, API 불필요)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT.parent))

import config as cfg  # noqa: E402
from gunma_samsung_analysis import (  # noqa: E402
    ROLE_LOAD_COLS,
    _synthetic_import_from_gunma,
    load_and_enhance,
    team_role_distribution,
)
from second_import_slot import (  # noqa: E402
    BENCHMARKS,
    ROLE_COACH_HINT,
    ROLES,
    _role_bounds,
    _vec,
    base_weighted_sum,
    build_kanter_one_roster,
    compute_slot,
    score_candidate,
)

STAT_FIELDS = [
    "p36_PPG", "p36_APG", "p36_RPG", "p36_3PA", "p36_SPG", "p36_BPG",
    "adv_USG%", "adv_AST%", "adv_TRB%", "adv_STL%", "adv_BLK%",
]

TEAM_META = {
    "LIN": {
        "code": "LIN",
        "short": "브렉스",
        "label": "브렉스 (전술 1순위)",
        "rank": "1순위 전술 벤치마크",
        "focus": "spacing · playmaking · 볼 movement",
        "film": "히에지마(PG) · DJ 뉴빌(PF)",
        "coachUse": "Role W가 가장 작을수록 전술 목표에 가깝습니다. spacing·볼 분배 film 1순위.",
    },
    "AIS": {
        "code": "AIS",
        "short": "미카와",
        "label": "미카와 (PF·로테)",
        "rank": "2순위 PF·로테이션",
        "focus": "PF 분업 · 로테 길이 · Gardner/Layman형",
        "film": "가드ner(hub PF) · 레이맨/스트레치 PF 분업",
        "coachUse": "브렉스와 W 차이가 작으면 둘 다 참고. 빅 2명 역할 나누기 film.",
    },
    "CCT": {
        "code": "CCT",
        "short": "군마",
        "label": "군마 (지형도)",
        "rank": "지형도·PG gap 진단",
        "focus": "로스터 지형 · Pass-First PG · Spot-Up",
        "film": "나카무라(PG) · 호시카와(스팟업)",
        "coachUse": "W가 크면 '완전히 군마처럼'은 어렵다는 뜻 — 부족한 타입 진단용.",
    },
}


def _normalize_row(row: pd.Series, name: str) -> dict:
    out = {"name": name}
    for c in STAT_FIELDS:
        v = float(row[c]) if c in row.index and pd.notna(row[c]) else 0.0
        if c.startswith("adv_") and v > 1.5:
            v = v / 100.0
        out[c] = round(v, 6)
    out["avg_MPG"] = round(float(row.get("avg_MPG", 28)), 1)
    return out


def _score_at_mpg(
    candidate: dict,
    base_raw: np.ndarray,
    samsung,
    pool,
    code: str,
    label: str,
    mpg: float,
) -> dict:
    slot = compute_slot(samsung, pool, code, label, weight_by_mpg=True, expected_mpg=mpg)
    bl = pool[(pool["league"] == "B.LEAGUE") & (pool["team_code"] == code)]
    target = _vec(team_role_distribution(bl, weight_by_mpg=True))
    ideal_v = _vec(slot.ideal_role_vector)
    row = pd.Series({**candidate, "Player": candidate["name"], "avg_MPG": mpg})
    scored = score_candidate(row, base_raw, target, ideal_v, mpg, slot.w_one, slot.w_optimal)
    return {
        "wOne": slot.w_one,
        "wOptimal": slot.w_optimal,
        "ideal": [round(float(x), 6) for x in ideal_v],
        "teamGapOne": slot.team_gap_one,
        "score": scored,
    }



def _load_report_ref() -> dict:
    out = {}
    paths = {
        "woodbury": cfg.REPORT_ROBUST_DIR / "analysis_meta.json",
        "layman": cfg.REPORT_ROBUST_LAYMAN_DIR / "analysis_meta.json",
    }
    team_keys = {
        "LIN": "Utsunomiya Brex",
        "AIS": "SeaHorses Mikawa",
        "CCT": "Gunma Crane Thunders",
    }
    for preset, path in paths.items():
        if not path.exists():
            continue
        meta = json.loads(path.read_text(encoding="utf-8"))
        sens = meta.get("stretch_pf_sensitivity", {})
        out[preset] = {
            code: round(sens[team_keys[code]]["w_dual_import"], 4)
            for code in team_keys
            if team_keys[code] in sens
        }
    return out


def export(*, mpg_min: int = 18, mpg_max: int = 36) -> None:
    samsung, gunma, pool = load_and_enhance(cfg.EXCLUDED_PLAYERS)
    one_df = build_kanter_one_roster(samsung)
    base_raw = base_weighted_sum(one_df, weight_by_mpg=True)
    bounds = _role_bounds(pool)

    bl = pool[pool["league"] == "B.LEAGUE"]
    layman_row = bl[(bl["team_code"] == "AIS") & (bl["Player"].str.contains("Layman", case=False, na=False))]
    if layman_row.empty:
        raise ValueError("Jake Layman (AIS) not found")
    woodbury_row = _synthetic_import_from_gunma(gunma, "Terrance Woodbury", "Woodbury (calc)")

    presets = {
        "layman": _normalize_row(layman_row.iloc[0], "제이크 레이맨 (SeaHorses Mikawa)"),
        "woodbury": _normalize_row(woodbury_row, "테런스 우드버리 (Stretch PF placeholder)"),
    }

    targets = {}
    for label, code in BENCHMARKS.items():
        tdf = bl[bl["team_code"] == code]
        targets[code] = [round(v, 6) for v in _vec(team_role_distribution(tdf, weight_by_mpg=True))]

    ideals_by_mpg: dict[str, dict] = {}
    for mpg in range(mpg_min, mpg_max + 1):
        ideals_by_mpg[str(mpg)] = {}
        for label, code in BENCHMARKS.items():
            slot = compute_slot(samsung, pool, code, label, weight_by_mpg=True, expected_mpg=float(mpg))
            ideal_v = _vec(slot.ideal_role_vector)
            ideals_by_mpg[str(mpg)][code] = {
                "wOne": slot.w_one,
                "wOptimal": slot.w_optimal,
                "ideal": [round(float(x), 6) for x in ideal_v],
                "teamGapOne": slot.team_gap_one,
            }

    presetScores = {}
    for pid, cand in presets.items():
        mpg = float(cand["avg_MPG"])
        presetScores[pid] = {}
        for label, code in BENCHMARKS.items():
            pack = _score_at_mpg(cand, base_raw, samsung, pool, code, label, mpg)
            s = pack["score"]
            presetScores[pid][code] = {
                "wOne": pack["wOne"],
                "wOptimal": pack["wOptimal"],
                "wAfter": s["w_after"],
                "improvePct": s["improve_pct_vs_one"],
                "deltaOpt": s["delta_from_optimal_w"],
                "verdict": s["verdict"],
            }

    payload = {
        "version": 2,
        "method": "Role W 역산 · MPG 가중 · Python second_import_slot.py 동일",
        "roles": ROLES,
        "roleLoadCols": ROLE_LOAD_COLS,
        "roleCoachHint": ROLE_COACH_HINT,
        "teamMeta": TEAM_META,
        "statFields": STAT_FIELDS,
        "baseRaw": [round(float(x), 6) for x in base_raw],
        "boundsHi": [round(float(b[1]), 6) for b in bounds],
        "targets": targets,
        "benchmarks": [{"code": code, "label": label} for label, code in BENCHMARKS.items()],
        "defaultPreset": "layman",
        "presets": presets,
        "presetScores": presetScores,
        "reportReference": _load_report_ref(),
        "idealsByMpg": ideals_by_mpg,
    }

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "baseline.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    (DATA / "baseline.js").write_text(
        "window.BASELINE = " + json.dumps(payload, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"Exported {DATA / 'baseline.json'}")
    for pid, cand in presets.items():
        print(f"  preset {pid}: {cand['name']} MPG={cand['avg_MPG']}")


if __name__ == "__main__":
    export()

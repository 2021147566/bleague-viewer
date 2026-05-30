#!/usr/bin/env python3
"""계산기(calc) ↔ 벤치마크 보고서 Role W parity 검증."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT.parent
sys.path.insert(0, str(RESEARCH))

import config as cfg  # noqa: E402
from gunma_samsung_analysis import (  # noqa: E402
    _synthetic_import_from_gunma,
    load_and_enhance,
    role_load_vector,
)
from rosters import build_rosters, role_wasserstein  # noqa: E402
from second_import_slot import (  # noqa: E402
    _vec,
    base_weighted_sum,
    build_kanter_one_roster,
    compute_slot,
    score_candidate,
    team_w,
)

BASELINE = ROOT / "data" / "baseline.json"
REPORT_WOOD = cfg.REPORT_ROBUST_DIR / "analysis_meta.json"
REPORT_LAY = cfg.REPORT_ROBUST_LAYMAN_DIR / "analysis_meta.json"

TEAMS = [
    ("Utsunomiya Brex", "LIN", "Brex"),
    ("SeaHorses Mikawa", "AIS", "Mikawa"),
    ("Gunma Crane Thunders", "CCT", "Gunma"),
]


def js_wasserstein(u_weights, v_weights):
    n = len(u_weights)
    positions = list(range(n))
    u_sum = sum(u_weights) or 1
    v_sum = sum(v_weights) or 1
    u = [w / u_sum for w in u_weights]
    v = [w / v_sum for w in v_weights]
    all_values = sorted(positions + positions)
    u_cum = [0.0]
    v_cum = [0.0]
    for i in range(n):
        u_cum.append(u_cum[-1] + u[i])
        v_cum.append(v_cum[-1] + v[i])
    w = 0.0
    for i in range(len(all_values) - 1):
        x = all_values[i]
        delta = all_values[i + 1] - x
        if delta == 0:
            continue
        ui = sum(1 for p in positions if p <= x)
        vi = ui
        w += abs(u_cum[ui] / u_cum[n] - v_cum[vi] / v_cum[n]) * delta
    return w


def js_team_w(base_raw, mpg, import_v, target):
    combined = [b + mpg * iv for b, iv in zip(base_raw, import_v)]
    s = sum(combined) or 1
    d = [c / s for c in combined]
    return js_wasserstein(target, d)


def candidate_series(row: pd.Series, label: str) -> pd.Series:
    s = row.copy()
    s["Player"] = label
    return s


def main() -> int:
    samsung, gunma, pool = load_and_enhance(cfg.EXCLUDED_PLAYERS)
    one_df = build_kanter_one_roster(samsung)
    base_raw = base_weighted_sum(one_df, weight_by_mpg=True)

    bl = pool[pool["league"] == "B.LEAGUE"]
    layman_row = bl[(bl["team_code"] == "AIS") & (bl["Player"].str.contains("Layman", case=False, na=False))].iloc[0]
    woodbury_row = _synthetic_import_from_gunma(
        gunma, "Terrance Woodbury", "Woodbury (calc compare)",
    )

    profiles = {
        "layman": {"row": layman_row, "mpg": float(layman_row["avg_MPG"]), "report": REPORT_LAY, "dual": "layman"},
        "woodbury": {"row": woodbury_row, "mpg": float(woodbury_row.get("avg_MPG", 28)), "report": REPORT_WOOD, "dual": "woodbury"},
    }

    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else None
    fails = 0

    print("=" * 72)
    print("계산기 ↔ 보고서 parity (dual W = w_dual_import, calc = W_after)")
    print("=" * 72)

    for pname, prof in profiles.items():
        report_meta = json.loads(prof["report"].read_text(encoding="utf-8"))
        rosters = build_rosters(samsung, gunma, pool, weight_by_mpg=True, dual_profile=prof["dual"])
        cand = candidate_series(prof["row"], prof["row"].get("Player", pname))
        mpg = prof["mpg"]
        iv = _vec(role_load_vector(cand))

        print(f"\n### {pname.upper()} (MPG={mpg})")
        print(f"{'bench':<8} {'report':>8} {'roster':>8} {'slot_py':>8} {'js':>8} {'baseline':>8} OK?")
        print("-" * 56)

        for team_name, code, _ in TEAMS:
            bl_team = pool[(pool["league"] == "B.LEAGUE") & (pool["team_code"] == code)]
            w_roster = role_wasserstein(rosters["s2627_dual"]["role_dist"], bl_team, weight_by_mpg=True)
            w_report = report_meta["stretch_pf_sensitivity"][team_name]["w_dual_import"]

            slot = compute_slot(samsung, pool, code, code, weight_by_mpg=True, expected_mpg=mpg)
            from gunma_samsung_analysis import team_role_distribution

            target = _vec(team_role_distribution(bl_team, weight_by_mpg=True))
            scored = score_candidate(cand, base_raw, target, _vec(slot.ideal_role_vector), mpg, slot.w_one, slot.w_optimal)
            w_slot = scored["w_after"]

            w_js = round(js_team_w(base_raw.tolist(), mpg, iv.tolist(), target.tolist()), 4)

            w_base = None
            if baseline:
                ps = baseline.get("presetScores", {}).get(pname, {})
                w_base = ps.get(code, {}).get("wAfter") if code in ps else None

            ok_report = abs(w_roster - w_report) < 0.0002
            ok_slot_roster = abs(w_slot - w_roster) < 0.0002
            ok_js = abs(w_js - w_slot) < 0.0002
            ok = ok_report and ok_slot_roster and ok_js
            if not ok:
                fails += 1

            base_s = f"{w_base:>8.4f}" if w_base is not None else "     n/a"
            print(
                f"{code:<8} {w_report:>8.4f} {w_roster:>8.4f} {w_slot:>8.4f} {w_js:>8.4f} {base_s} "
                f"{'OK' if ok else 'FAIL'}"
            )
            if not ok_report:
                print(f"  ! report vs roster Δ={w_report - w_roster:+.4f}")
            if not ok_slot_roster:
                print(f"  ! slot_py vs roster Δ={w_slot - w_roster:+.4f}")
            if not ok_js:
                print(f"  ! js vs slot_py Δ={w_js - w_slot:+.4f}")
            if w_base is not None and abs(w_base - w_slot) >= 0.0002:
                print(f"  ! baseline.json vs slot_py Δ={w_base - w_slot:+.4f}")
                fails += 1

    print("\n" + "=" * 72)
    print(f"Done - {fails} failure(s)")
    return fails


if __name__ == "__main__":
    raise SystemExit(main())

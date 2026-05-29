#!/usr/bin/env python3
"""bl_25-26_clustered_result.xlsx -> player_clusters.json with fuzzy name matching."""
from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

from name_utils import canonical_player_en, player_name_key

ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "bl_25-26_clustered_result.xlsx"
ROSTERS = ROOT / "bleague-rosters.json"
OVERRIDES = ROOT / "cluster_match_overrides.json"
OUT = ROOT / "player_clusters.json"

_SUFFIXES = frozenset({"jr", "sr", "ii", "iii"})
_MIN_SCORE = 0.80
_MIN_SCORE_SAME_TEAM = 0.70
_MIN_FAMILY = 0.58
_MIN_FAMILY_ANY = 0.62
_NICKNAMES = {
    "chris": "christopher",
    "christopher": "chris",
    "mike": "michael",
    "michael": "mike",
    "joe": "joseph",
    "joseph": "joe",
    "dave": "david",
    "david": "dave",
}

# bleague team_id -> 2025-26 xlsx Team code (없으면 팀 제한 없이 이름만 매칭)
ROSTER_TO_EXCEL_TEAM: dict[str, str | None] = {
    "levanga": "LEV",
    "sendai": "SEND",
    "akita": "AKIT",
    "ibaraki": "IR",
    "utsunomiya": "LIN",
    "gunma": "CCT",
    "altiri_chiba": "ALT",
    "chiba_jets": "CHI",
    "alvark_tokyo": "TOY",
    "sun_rockers": "HIT",
    "kawasaki": "BRAV",
    "yokohama": "YOKO",
    "koshigaya": "KOSH",
    "shinshu": None,
    "sanen": "SAN",
    "mikawa": "AIS",
    "nagoya_dd": "NDD",
    "shiga": "SHIG",
    "kyoto": "KYOT",
    "osaka": "OSAK",
    "kobe": None,
    "shimane": "SHIM",
    "hiroshima": "HIR",
    "saga": "SAGA",
    "nagasaki": "NAG",
    "ryukyu": "RYUK",
    "toyama": "TOY",
    "fighting_eagles": "NFF",
}


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def name_tokens(name: str) -> set[str]:
    s = strip_accents(name).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return {p for p in s.split() if len(p) > 1 and p not in _SUFFIXES}


def split_name(name: str) -> tuple[str, str]:
    parts = strip_accents(name).split()
    clean = [p for p in parts if p.lower() not in _SUFFIXES]
    if not clean:
        return "", ""
    if len(clean) == 1:
        return clean[0].lower(), ""
    return " ".join(clean[:-1]).lower(), clean[-1].lower()


def norm_given(given: str) -> str:
    if not given:
        return ""
    first = given.split()[0]
    return _NICKNAMES.get(first, first)


def family_ratio(a: str, b: str) -> float:
    _, fa = split_name(a)
    _, fb = split_name(b)
    if not fa or not fb:
        return 0.0
    return SequenceMatcher(None, fa, fb).ratio()


def given_ratio(a: str, b: str) -> float:
    ga, _ = split_name(a)
    gb, _ = split_name(b)
    if not ga or not gb:
        return 0.0
    ga_n, gb_n = norm_given(ga), norm_given(gb)
    return max(
        SequenceMatcher(None, ga, gb).ratio(),
        SequenceMatcher(None, ga_n, gb_n).ratio(),
    )


def token_ratio(a: str, b: str) -> float:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    if not inter:
        return 0.0
    return len(inter) / min(len(ta), len(tb))


def combined_score(roster_en: str, excel_en: str) -> float:
    """성·이름 구조 + 토큰 겹침 (정렬 키만 쓰면 Haruki Ito≠Naito 오매칭)."""
    fr = family_ratio(roster_en, excel_en)
    gr = given_ratio(roster_en, excel_en)
    tr = token_ratio(roster_en, excel_en)
    if fr >= 0.65:
        structured = 0.42 * fr + 0.43 * gr + 0.15 * tr
    elif gr >= 0.95 and len(split_name(roster_en)[0].split()) == 1:
        # 희귀 다단어 이름(예: Tshilidzi) + 성만 다를 때
        structured = 0.35 * fr + 0.55 * gr + 0.10 * tr
    else:
        structured = max(0.55 * gr + 0.45 * fr, tr)
    return max(structured, tr)


def passes_threshold(score: float, fr: float, same_team: bool) -> bool:
    min_score = _MIN_SCORE_SAME_TEAM if same_team else _MIN_SCORE
    min_family = _MIN_FAMILY if same_team else _MIN_FAMILY_ANY
    if score < min_score:
        return False
    return fr >= min_family or score >= 0.88


def load_overrides() -> dict[str, str]:
    if not OVERRIDES.is_file():
        return {}
    data = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in (data.get("by_player_id") or {}).items()}


def build_excel_index(df: pd.DataFrame) -> tuple[list[dict], dict[str, str]]:
    rows: list[dict] = []
    by_key: dict[str, str] = {}
    for _, row in df.iterrows():
        name = str(row.get("Player", "")).strip()
        cluster = str(row.get("cluster_name", "") or row.get("position_label", "")).strip()
        team = str(row.get("Team", "")).strip()
        if not name or not cluster or cluster == "nan":
            continue
        entry = {
            "name": name,
            "key": player_name_key(name),
            "team": team,
            "cluster": cluster,
        }
        rows.append(entry)
        by_key.setdefault(entry["key"], cluster)
    return rows, by_key


def find_best_match(
    roster_en: str,
    team_id: str,
    excel_rows: list[dict],
    by_key: dict[str, str],
) -> tuple[str, float, str]:
    canonical = canonical_player_en(roster_en)
    key = player_name_key(canonical)
    if key in by_key:
        return by_key[key], 1.0, "exact"

    excel_team = ROSTER_TO_EXCEL_TEAM.get(team_id)
    best_cluster = ""
    best_score = 0.0
    best_name = ""
    best_method = ""
    best_fr = 0.0

    for ex in excel_rows:
        if excel_team and ex["team"] != excel_team:
            continue
        score = combined_score(canonical, ex["name"])
        fr = family_ratio(canonical, ex["name"])
        if score > best_score:
            best_score = score
            best_cluster = ex["cluster"]
            best_name = ex["name"]
            best_method = "fuzzy_team"
            best_fr = fr

    if best_cluster and passes_threshold(best_score, best_fr, same_team=True):
        return best_cluster, best_score, best_method

    best_cluster = ""
    best_score = 0.0
    best_name = ""
    best_fr = 0.0
    for ex in excel_rows:
        score = combined_score(canonical, ex["name"])
        fr = family_ratio(canonical, ex["name"])
        if score > best_score:
            best_score = score
            best_cluster = ex["cluster"]
            best_name = ex["name"]
            best_method = "fuzzy_any"
            best_fr = fr

    if best_cluster and passes_threshold(best_score, best_fr, same_team=False):
        return best_cluster, best_score, best_method

    return "", best_score, ""


def main() -> None:
    df = pd.read_excel(XLSX)
    excel_rows, by_key = build_excel_index(df)
    overrides = load_overrides()
    rosters = json.loads(ROSTERS.read_text(encoding="utf-8"))

    by_id: dict[str, str] = {}
    meta: dict[str, dict] = {}
    stats = {"exact": 0, "fuzzy_team": 0, "fuzzy_any": 0, "override": 0, "none": 0}

    for team_id, team in rosters.get("teams", {}).items():
        for p in team.get("players", []):
            pid = str(p.get("player_id", "")).strip()
            en = p.get("name_en") or ""
            if not pid:
                continue

            if pid in overrides:
                by_id[pid] = overrides[pid]
                meta[pid] = {"method": "override", "score": 1.0}
                stats["override"] += 1
                continue

            cluster, score, method = find_best_match(en, team_id, excel_rows, by_key)
            by_id[pid] = cluster
            if cluster:
                stats[method] += 1
            else:
                stats["none"] += 1

    matched = sum(1 for v in by_id.values() if v)
    out = {
        "source": XLSX.name,
        "season": str(df["season"].iloc[0]) if len(df) else "",
        "roster_season": rosters.get("season", ""),
        "matched": matched,
        "total": len(by_id),
        "stats": stats,
        "by_player_id": by_id,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Wrote {OUT.name}: {matched}/{len(by_id)} "
        f"(exact={stats['exact']}, fuzzy_team={stats['fuzzy_team']}, "
        f"fuzzy_any={stats['fuzzy_any']}, override={stats['override']}, none={stats['none']})",
        flush=True,
    )


if __name__ == "__main__":
    main()

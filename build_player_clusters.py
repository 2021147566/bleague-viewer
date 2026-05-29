#!/usr/bin/env python3
"""clustering_syk_clustered.xlsx -> player_clusters.json (player_id -> cluster_name)."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from name_utils import player_name_key

ROOT = Path(__file__).resolve().parent
XLSX = ROOT / "clustering_syk_clustered.xlsx"
ROSTERS = ROOT / "bleague-rosters.json"
OUT = ROOT / "player_clusters.json"


def main() -> None:
    df = pd.read_excel(XLSX)
    by_name: dict[str, str] = {}
    for _, row in df.iterrows():
        name = str(row.get("Player", "")).strip()
        cluster = str(row.get("cluster_name", "")).strip()
        if not name or not cluster or cluster == "nan":
            continue
        key = player_name_key(name)
        if key:
            by_name[key] = cluster

    data = json.loads(ROSTERS.read_text(encoding="utf-8"))
    by_id: dict[str, str] = {}
    for team in data.get("teams", {}).values():
        for p in team.get("players", []):
            pid = str(p.get("player_id", "")).strip()
            en = p.get("name_en") or ""
            if not pid:
                continue
            key = player_name_key(en)
            by_id[pid] = by_name.get(key, "")

    matched = sum(1 for v in by_id.values() if v)
    out = {
        "source": XLSX.name,
        "season": str(df["season"].iloc[0]) if len(df) else "",
        "matched": matched,
        "total": len(by_id),
        "by_player_id": by_id,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.name}: {matched}/{len(by_id)} players with cluster_name", flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Patch minutes stats into bleague-rosters.json for all players."""
import json
import time
import urllib.error
from datetime import date
from pathlib import Path

from crawl_bleague_rosters import fetch
from minutes_parser import parse_b1_minutes

ROSTERS = Path(__file__).with_name("bleague-rosters.json")


def main():
    data = json.loads(ROSTERS.read_text(encoding="utf-8"))
    total = sum(len(t["players"]) for t in data["teams"].values())
    n = 0
    for team in data["teams"].values():
        for p in team["players"]:
            n += 1
            pid = p["player_id"]
            try:
                html = fetch(f"https://www.bleague.jp/roster_detail/?PlayerID={pid}")
                p.update(parse_b1_minutes(html))
            except urllib.error.URLError as e:
                print(f"WARN {pid}: {e}", flush=True)
            if n % 20 == 0:
                print(f"  {n}/{total}...", flush=True)
            time.sleep(0.12)

    data["updated"] = date.today().isoformat()
    ROSTERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with_mins = sum(
        1
        for t in data["teams"].values()
        for p in t["players"]
        if p.get("minutes_avg_sec", 0) > 0
    )
    print(f"done {with_mins}/{total} players with minutes", flush=True)


if __name__ == "__main__":
    main()

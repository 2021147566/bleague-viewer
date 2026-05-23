#!/usr/bin/env python3
"""Refresh games/GS/minutes on all players."""
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
            try:
                html = fetch(f"https://www.bleague.jp/roster_detail/?PlayerID={p['player_id']}")
                p.update(parse_b1_minutes(html))
            except urllib.error.URLError as e:
                print(f"WARN {p['player_id']}: {e}", flush=True)
            if n % 40 == 0:
                print(f"  {n}/{total}...", flush=True)
            time.sleep(0.1)

    data["updated"] = date.today().isoformat()
    ROSTERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("done", flush=True)


if __name__ == "__main__":
    main()

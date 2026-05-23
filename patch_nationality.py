#!/usr/bin/env python3
"""Fix nationality fields in bleague-rosters.json."""
import json
import time
import urllib.error
from collections import Counter
from datetime import date
from pathlib import Path

from crawl_bleague_rosters import fetch, parse_nationality

ROSTERS = Path(__file__).with_name("bleague-rosters.json")


def main():
    data = json.loads(ROSTERS.read_text(encoding="utf-8"))
    total = sum(len(t["players"]) for t in data["teams"].values())
    counts: Counter[str] = Counter()
    n = 0
    for team in data["teams"].values():
        for p in team["players"]:
            n += 1
            pid = p["player_id"]
            try:
                html = fetch(f"https://www.bleague.jp/roster_detail/?PlayerID={pid}")
                p["nationality"] = parse_nationality(html)
            except urllib.error.URLError as e:
                print(f"WARN {pid}: {e}", flush=True)
            counts[p.get("nationality", "?")] += 1
            if n % 40 == 0:
                print(f"  {n}/{total}...", flush=True)
            time.sleep(0.1)

    data["updated"] = date.today().isoformat()
    ROSTERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("nationalities:", dict(counts.most_common()), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Parse 2025-26 season stats from roster_detail HTML."""
import re

TIME = re.compile(r"^(\d+):(\d{2})$")
INT = re.compile(r"^\d+$")

EMPTY = {
    "games": 0,
    "games_started": 0,
    "minutes_total": "",
    "minutes_avg": "",
    "minutes_total_sec": 0,
    "minutes_avg_sec": 0,
}


def time_to_sec(s: str) -> int:
    s = (s or "").strip()
    m = TIME.match(s)
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_league_row(html: str, league: str) -> dict | None:
    for row in re.finditer(r"<tr[^>]*>[\s\S]*?2025-26[\s\S]*?</tr>", html):
        cells = [
            c.strip()
            for c in re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", row.group(0))
            if c.strip()
        ]
        if len(cells) < 7 or cells[0] != "2025-26" or cells[1] != league:
            continue
        g, gs, total, avg = cells[3], cells[4], cells[5], cells[6]
        if not (INT.match(g) and INT.match(gs) and TIME.match(total) and TIME.match(avg)):
            continue
        return {
            "games": int(g),
            "games_started": int(gs),
            "minutes_total": total,
            "minutes_avg": avg,
            "minutes_total_sec": time_to_sec(total),
            "minutes_avg_sec": time_to_sec(avg),
        }
    return None


def parse_b1_minutes(html: str) -> dict:
    """Return 2025-26 stats (B1 preferred, else B2)."""
    for league in ("B1", "B2"):
        parsed = parse_league_row(html, league)
        if parsed:
            return parsed
    return dict(EMPTY)


if __name__ == "__main__":
    import urllib.request

    for pid in ["51000379", "51000528", "10850"]:
        html = urllib.request.urlopen(
            urllib.request.Request(
                f"https://www.bleague.jp/roster_detail/?PlayerID={pid}",
                headers={"User-Agent": "Mozilla/5.0"},
            ),
            timeout=30,
        ).read().decode("utf-8", "replace")
        print(pid, parse_b1_minutes(html))

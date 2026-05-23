#!/usr/bin/env python3
"""팀원 동부 시트 vs 우리 동부 — 팀원 명단 + O/X/△ 표시."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from export_research_sheet import (
    EAST_ORDER,
    HEADER_GRAY,
    ORIGINAL_SHEET,
    SPREADSHEET_ID,
    TEAM_NAME_GREEN,
    build_rows,
    get_sheets_creds,
    is_team_header_row,
    make_team_header,
    norm_team,
    parse_sheet_rows,
    read_sheet_values,
    reset_sheet_formatting,
)
from name_utils import canonical_player_en, player_name_key

ROSTERS_PATH = Path(__file__).resolve().parent / "bleague-rosters.json"
COMPARE_SHEET = "동부 비교"

TIER_LABEL = {"starter": "주전", "bench": "벤치"}

HEADERS = [
    "팀(EN)",
    "팀(KO)",
    "구분",
    "팀원 선수(EN)",
    "팀원 선수(KO)",
    "일치",
    "우리 구분",
    "우리 선수(EN)",
    "우리 선수(KO)",
]

MARK_SAME = "O"
MARK_NONE = "X"
MARK_TIER = "△"

COMPARE_COLS = len(HEADERS)
SUMMARY_HEADERS = ["팀(EN)", "팀(KO)", MARK_SAME, MARK_TIER, MARK_NONE]


def tier_key(entry: dict) -> str:
    tier = entry.get("tier") or ""
    if "주전" in tier:
        return "starter"
    if "벤치" in tier:
        return "bench"
    return "starter" if entry.get("rank", 99) <= 5 else "bench"


def tier_label(entry: dict) -> str:
    t = entry.get("tier") or ""
    if t:
        return t
    return "주전급 5명" if tier_key(entry) == "starter" else "벤치 핵심 4명"


def team_player_maps(rank_map: dict[tuple[str, int], dict]) -> dict[str, dict]:
    teams: dict[str, dict] = {}
    for entry in rank_map.values():
        team_norm = norm_team(entry["team"])
        if team_norm not in teams:
            teams[team_norm] = {
                "team": entry["team"],
                "team_ko": entry.get("team_ko") or "",
                "players": {},
            }
        elif not teams[team_norm]["team_ko"] and entry.get("team_ko"):
            teams[team_norm]["team_ko"] = entry["team_ko"]
        teams[team_norm]["players"][player_name_key(entry["player"])] = {
            "entry": entry,
            "tier": tier_key(entry),
        }
    return teams


def team_roster_ordered(rank_map: dict[tuple[str, int], dict], team_norm: str) -> list[dict]:
    rows = [entry for (t, _r), entry in rank_map.items() if t == team_norm]
    return sorted(rows, key=lambda e: e["rank"])


def match_mark(theirs_tier: str, ours: dict | None) -> str:
    if ours is None:
        return MARK_NONE
    if theirs_tier == ours["tier"]:
        return MARK_SAME
    return MARK_TIER


def build_compare_rows(theirs_map: dict, ours_map: dict) -> list[list]:
    theirs_teams = team_player_maps(theirs_map)
    ours_teams = team_player_maps(ours_map)

    team_order = sorted(
        theirs_teams.keys(),
        key=lambda t: team_roster_ordered(theirs_map, t)[0]["team"] if team_roster_ordered(theirs_map, t) else t,
    )
    only_ours = sorted(set(ours_teams) - set(theirs_teams))

    counts = {MARK_SAME: 0, MARK_TIER: 0, MARK_NONE: 0}
    team_summary: list[list] = []
    detail_rows: list[list] = []

    for team_norm in team_order:
        tmeta = theirs_teams[team_norm]
        ometa = ours_teams.get(team_norm, {"players": {}})
        team_en = tmeta["team"]
        team_ko = tmeta["team_ko"]
        roster = team_roster_ordered(theirs_map, team_norm)

        team_counts = {MARK_SAME: 0, MARK_TIER: 0, MARK_NONE: 0}

        detail_rows.append(make_team_header(team_en, team_ko, cols=COMPARE_COLS))

        for entry in roster:
            pn = player_name_key(entry["player"])
            tp = tmeta["players"].get(pn)
            op = ometa["players"].get(pn)
            mark = match_mark(tp["tier"], op) if tp else MARK_NONE
            counts[mark] += 1
            team_counts[mark] += 1

            detail_rows.append([
                "",
                "",
                tier_label(entry),
                canonical_player_en(entry["player"]),
                entry.get("player_ko", "") or (tp["entry"].get("player_ko", "") if tp else ""),
                mark,
                TIER_LABEL[op["tier"]] if op else "",
                canonical_player_en(op["entry"]["player"]) if op else "",
                op["entry"].get("player_ko", "") if op else "",
            ])

        team_summary.append([
            team_en,
            team_ko,
            team_counts[MARK_SAME],
            team_counts[MARK_TIER],
            team_counts[MARK_NONE],
        ])

    def team_label(team_norm: str, store: dict) -> str:
        m = store[team_norm]
        return f"{m['team']} / {m['team_ko']}" if m["team_ko"] else m["team"]

    rows: list[list] = [
        ["【동부 비교】"],
        ["범례", f"{MARK_SAME}=같은 구분(주전/벤치)  {MARK_TIER}=명단엔 있으나 구분만 다름  {MARK_NONE}=우리 9명에 없음"],
        ["팀원 시트", ORIGINAL_SHEET],
        [],
        ["우리 전용 팀 (팀원 시트 없음)", ", ".join(team_label(t, ours_teams) for t in only_ours) or "-"],
        [],
        ["전체", MARK_SAME, counts[MARK_SAME]],
        ["전체", MARK_TIER, counts[MARK_TIER]],
        ["전체", MARK_NONE, counts[MARK_NONE]],
        [],
        SUMMARY_HEADERS,
    ]
    rows.extend(team_summary)
    rows.append([])
    rows.append(HEADERS)
    rows.extend(detail_rows)
    return rows


def _gray_header_request(sheet_id: int, row_idx: int, num_cols: int) -> dict:
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": row_idx,
                "endRowIndex": row_idx + 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": HEADER_GRAY,
                    "textFormat": {"bold": True},
                    "horizontalAlignment": "CENTER",
                },
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
        },
    }


def apply_compare_formatting(service, sheet_id: int, rows: list[list]) -> None:
    detail_header_idx = next((i for i, row in enumerate(rows) if row == HEADERS), None)
    if detail_header_idx is None:
        return

    summary_header_idx = next((i for i, row in enumerate(rows) if row == SUMMARY_HEADERS), None)
    num_rows = max(len(rows), detail_header_idx + 1)
    reset_sheet_formatting(
        service,
        sheet_id,
        num_rows=num_rows + 5,
        num_cols=COMPARE_COLS,
        freeze_rows=0,
    )

    requests: list[dict] = [_gray_header_request(sheet_id, detail_header_idx, COMPARE_COLS)]
    if summary_header_idx is not None:
        requests.append(_gray_header_request(sheet_id, summary_header_idx, len(SUMMARY_HEADERS)))

    mark_col = HEADERS.index("일치")
    for i, row in enumerate(rows[detail_header_idx + 1 :], start=detail_header_idx + 1):
        if not row:
            continue
        if is_team_header_row(row, cols=COMPARE_COLS):
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": i,
                        "endRowIndex": i + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": COMPARE_COLS,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": TEAM_NAME_GREEN,
                            "textFormat": {"bold": True, "fontSize": 11},
                        },
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                },
            })
            continue

        if len(row) <= mark_col:
            continue

        mark = row[mark_col]
        mark_bg = None
        if mark == MARK_SAME:
            mark_bg = {"red": 0.85, "green": 0.95, "blue": 0.85}
        elif mark == MARK_NONE:
            mark_bg = {"red": 0.95, "green": 0.85, "blue": 0.85}
        elif mark == MARK_TIER:
            mark_bg = {"red": 1.0, "green": 0.95, "blue": 0.8}
        if mark_bg:
            requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": i,
                        "endRowIndex": i + 1,
                        "startColumnIndex": mark_col,
                        "endColumnIndex": mark_col + 1,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": mark_bg,
                            "horizontalAlignment": "CENTER",
                            "textFormat": {"bold": True, "fontSize": 12},
                        },
                    },
                    "fields": "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)",
                },
            })

    compare_col_widths = [170, 140, 100, 170, 120, 52, 72, 170, 120]
    for idx, px in enumerate(compare_col_widths):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": idx,
                    "endIndex": idx + 1,
                },
                "properties": {"pixelSize": px},
                "fields": "pixelSize",
            },
        })

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests},
    ).execute()


def upload_compare_sheet(service, rows: list[list]) -> str:
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}
    if COMPARE_SHEET not in existing:
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": COMPARE_SHEET}}}]},
        ).execute()
        sheet_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    else:
        sheet_id = existing[COMPARE_SHEET]

    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{COMPARE_SHEET}'!A:I",
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{COMPARE_SHEET}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()
    apply_compare_formatting(service, sheet_id, rows)
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={sheet_id}"


def sync_compare_sheet(service, teams: dict) -> str:
    ours_raw = build_rows(teams, EAST_ORDER)
    theirs_raw = read_sheet_values(service, ORIGINAL_SHEET)
    theirs_map = parse_sheet_rows(theirs_raw)
    ours_map = parse_sheet_rows(ours_raw)
    compare_rows = build_compare_rows(theirs_map, ours_map)
    return upload_compare_sheet(service, compare_rows)


def main() -> int:
    creds = get_sheets_creds(interactive=False)
    if creds is None:
        print("Google Sheets 인증 필요", file=sys.stderr)
        return 1

    from googleapiclient.discovery import build

    service = build("sheets", "v4", credentials=creds)

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    url = sync_compare_sheet(service, data["teams"])
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())

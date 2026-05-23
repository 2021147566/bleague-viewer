#!/usr/bin/env python3
"""B리그 코어 로테이션(주전5+벤치4) 리서치 시트 내보내기 / Google Sheets 업로드."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from name_utils import (
    canonical_player_en,
    merge_team_ko_maps,
    norm_name,
    player_name_key,
    team_ko_extra,
)

ROOT = Path(__file__).resolve().parent.parent
ROSTERS_PATH = Path(__file__).resolve().parent / "bleague-rosters.json"
SPREADSHEET_ID = "1SyC86Hvp-Onp5EBi_AgJ37-fqapN_j-gpDIFxKhbg1Y"
ORIGINAL_SHEET = "시트1"

STARTER_COUNT = 5
BENCH_COUNT = 4
ROTATION_COUNT = STARTER_COUNT + BENCH_COUNT
MIN_GAMES = 5

WEST_ORDER = [
    "shinshu", "sanen", "mikawa", "nagoya_dd", "shiga", "kyoto", "osaka",
    "kobe", "shimane", "hiroshima", "saga", "nagasaki", "ryukyu",
]

EAST_ORDER = [
    "levanga", "sendai", "akita", "ibaraki", "utsunomiya", "gunma", "altiri_chiba",
    "chiba_jets", "alvark_tokyo", "sun_rockers", "kawasaki", "yokohama", "koshigaya",
]

TEAM_NAME_EN = {
    "levanga": "Levanga Hokkaido",
    "sendai": "Sendai 89ers",
    "akita": "Akita Northern Happinets",
    "ibaraki": "Ibaraki Robots",
    "utsunomiya": "Utsunomiya Brex",
    "gunma": "Gunma Crane Thunders",
    "altiri_chiba": "Altiri Chiba",
    "chiba_jets": "Chiba Jets",
    "alvark_tokyo": "Alvark Tokyo",
    "sun_rockers": "Sunrockers Shibuya",
    "kawasaki": "Kawasaki Brave Thunders",
    "yokohama": "Yokohama B-Corsairs",
    "koshigaya": "Koshigaya Alphas",
    "toyama": "Toyama Grouses",
    "shinshu": "Shinshu Brave Warriors",
    "sanen": "San-en NeoPhoenix",
    "mikawa": "SeaHorses Mikawa",
    "nagoya_dd": "Nagoya Diamond Dolphins",
    "shiga": "Shiga Lakes",
    "kyoto": "Kyoto Hannaryz",
    "osaka": "Osaka Evessa",
    "kobe": "Kobe Storks",
    "shimane": "Shimane Susanoo Magic",
    "hiroshima": "Hiroshima Dragonflies",
    "saga": "Saga Ballooners",
    "nagasaki": "Nagasaki Velca",
    "ryukyu": "Ryukyu Golden Kings",
}

RESEARCH_COLS = 8

RESEARCH_HEADERS = [
    "팀(EN)", "팀(KO)", "순위", "구분", "선수(EN)", "선수(KO)", "GS", "MIN",
]

# Google Sheets light green (팀원 시트 팀명 배경과 유사)
TEAM_NAME_GREEN = {"red": 0.714, "green": 0.843, "blue": 0.659}
HEADER_GRAY = {"red": 0.933, "green": 0.933, "blue": 0.933}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}


def is_header_row(row: list) -> bool:
    return len(row) >= len(RESEARCH_HEADERS) and row[: len(RESEARCH_HEADERS)] == RESEARCH_HEADERS


def is_team_header_row(row: list, *, cols: int = RESEARCH_COLS) -> bool:
    """팀 구분용 초록 헤더 행: A열 팀명 있고, 순위/구분 칸(3열) 비어 있음."""
    if len(row) < 2 or not str(row[0]).strip():
        return False
    third = str(row[2]).strip() if len(row) > 2 else ""
    return third == ""


def make_team_header(team_en: str, team_ko: str, *, cols: int = RESEARCH_COLS) -> list:
    row = [team_en, team_ko, "", "", "", "", "", ""]
    return row[:cols] + [""] * max(0, cols - len(row))


def layout_with_team_headers(flat_rows: list[list], *, cols: int = RESEARCH_COLS) -> list[list]:
    """팀별 첫 줄=초록 헤더, 선수 줄=팀명 칸 비움."""
    out: list[list] = []
    prev_team: str | None = None
    for row in flat_rows:
        if not row:
            continue
        team_en = str(row[0]).strip()
        team_ko = str(row[1]).strip() if len(row) > 1 else ""
        if team_en and team_en != prev_team:
            out.append(make_team_header(team_en, team_ko, cols=cols))
            prev_team = team_en
        player = row[:cols] + [""] * max(0, cols - len(row))
        player[0] = ""
        player[1] = ""
        out.append(player[:cols])
    return out


def prepend_header(rows: list[list]) -> list[list]:
    if rows and is_header_row(rows[0]):
        return rows
    return [RESEARCH_HEADERS] + rows


def team_header_row_indices(rows: list[list], *, cols: int = RESEARCH_COLS) -> list[int]:
    """헤더 포함 rows 기준, 각 팀 초록 헤더 행 index (0-based)."""
    indices: list[int] = []
    start = 1 if rows and is_header_row(rows[0]) else 0
    for i, row in enumerate(rows[start:], start=start):
        if is_team_header_row(row, cols=cols):
            indices.append(i)
    return indices


def reset_sheet_formatting(
    service,
    sheet_id: int,
    *,
    num_rows: int,
    num_cols: int,
    freeze_rows: int = 1,
) -> None:
    """업로드 직전 잔여 서식 제거 + 흰 배경 초기화."""
    requests: list[dict] = [
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": freeze_rows},
                },
                "fields": "gridProperties.frozenRowCount",
            },
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": max(num_rows, 1),
                    "startColumnIndex": 0,
                    "endColumnIndex": num_cols,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": WHITE,
                        "textFormat": {"bold": False, "fontSize": 10},
                        "horizontalAlignment": "LEFT",
                    },
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
            },
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests},
    ).execute()


def apply_research_formatting(service, sheet_id: int, rows: list[list]) -> None:
    num_rows = max(len(rows), 1)
    reset_sheet_formatting(service, sheet_id, num_rows=num_rows + 5, num_cols=RESEARCH_COLS)

    requests: list[dict] = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": RESEARCH_COLS,
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
        },
    ]
    for row_idx in team_header_row_indices(rows):
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": row_idx,
                    "endRowIndex": row_idx + 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": RESEARCH_COLS,
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

    col_widths = [180, 150, 48, 110, 180, 130, 48, 56]
    for idx, px in enumerate(col_widths):
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

    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": requests},
        ).execute()


def norm_team(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def build_roster_lookups(teams: dict) -> tuple[dict[str, str], dict[str, str]]:
    team_en_to_ko: dict[str, str] = {}
    for team_id, team in teams.items():
        en = TEAM_NAME_EN.get(team_id)
        if en:
            team_en_to_ko[norm_team(en)] = team.get("name_korean") or ""
    team_en_to_ko = merge_team_ko_maps(team_en_to_ko)

    player_en_to_ko: dict[str, str] = {}
    for team in teams.values():
        for player in team.get("players", []):
            en = player.get("name_en") or player.get("name_jp") or ""
            ko = player.get("name_korean") or ""
            if en and ko:
                player_en_to_ko[player_name_key(en)] = ko
    return team_en_to_ko, player_en_to_ko


def lookup_team_ko(team_en: str, team_en_to_ko: dict[str, str]) -> str:
    if team_en in team_ko_extra():
        return team_ko_extra()[team_en]
    return team_en_to_ko.get(norm_team(team_en), "")


def lookup_player_ko(player_en: str, player_en_to_ko: dict[str, str]) -> str:
    return player_en_to_ko.get(player_name_key(player_en), "")


def to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


def enrich_legacy_rows(
    values: list[list],
    team_en_to_ko: dict[str, str],
    player_en_to_ko: dict[str, str],
) -> list[list]:
    """6열(영문만) 또는 8열 시트를 한글 컬럼 포함 8열로 정규화."""
    rows: list[list] = []
    for row in values:
        if not row or not str(row[0]).strip():
            continue
        if is_header_row(row):
            continue
        if len(row) >= RESEARCH_COLS:
            try:
                rank = int(float(row[2]))
            except (TypeError, ValueError):
                continue
            team_en = str(row[0]).strip()
            player_en = canonical_player_en(str(row[4]).strip())
            team_ko = str(row[1]).strip() if str(row[1]).strip() else lookup_team_ko(team_en, team_en_to_ko)
            player_ko = str(row[5]).strip() if str(row[5]).strip() else lookup_player_ko(player_en, player_en_to_ko)
            rows.append([
                team_en,
                team_ko,
                rank,
                str(row[3]).strip(),
                player_en,
                player_ko,
                row[6] if len(row) > 6 else "",
                row[7] if len(row) > 7 else "",
            ])
            continue

        try:
            rank = int(float(row[1]))
        except (TypeError, ValueError):
            continue
        team_en = str(row[0]).strip()
        player_en = canonical_player_en(str(row[3]).strip())
        rows.append([
            team_en,
            lookup_team_ko(team_en, team_en_to_ko),
            rank,
            str(row[2]).strip() if len(row) > 2 else "",
            player_en,
            lookup_player_ko(player_en, player_en_to_ko),
            row[4] if len(row) > 4 else "",
            row[5] if len(row) > 5 else "",
        ])
    return rows


def rank_by(players: list[dict], key: str) -> dict[str, int]:
    sorted_players = sorted(players, key=lambda p: p.get(key) or 0, reverse=True)
    return {p["player_id"]: i + 1 for i, p in enumerate(sorted_players)}


def ranked_core_ids(players: list[dict]) -> list[str]:
    pool = [
        p for p in players
        if (p.get("games") or 0) >= MIN_GAMES or (p.get("minutes_avg_sec") or 0) > 0
    ]
    if not pool:
        return []

    if not any((p.get("games_started") or 0) > 0 for p in pool):
        pool.sort(key=lambda p: p.get("minutes_avg_sec") or 0, reverse=True)
        return [p["player_id"] for p in pool[:ROTATION_COUNT]]

    gs_rank = rank_by(pool, "games_started")
    min_rank = rank_by(pool, "minutes_avg_sec")
    scored = [
        (
            (gs_rank[p["player_id"]] or 99) + (min_rank[p["player_id"]] or 99),
            p["player_id"],
        )
        for p in pool
    ]
    scored.sort(key=lambda x: (x[0], x[1]))
    return [pid for _, pid in scored[:ROTATION_COUNT]]


def avg_min_decimal(player: dict) -> float:
    sec = player.get("minutes_avg_sec") or 0
    return round(sec / 60, 1)


def build_rows(teams: dict, order: list[str]) -> list[list]:
    team_en_to_ko, player_en_to_ko = build_roster_lookups(teams)
    rows: list[list] = []
    for team_id in order:
        team = teams.get(team_id)
        if not team:
            continue
        team_name = TEAM_NAME_EN.get(team_id, team.get("name_korean", team_id))
        team_ko = team.get("name_korean") or lookup_team_ko(team_name, team_en_to_ko)
        rows.append(make_team_header(team_name, team_ko))
        by_id = {p["player_id"]: p for p in team.get("players", [])}
        ranked = ranked_core_ids(team.get("players", []))
        for i, pid in enumerate(ranked, start=1):
            p = by_id[pid]
            tier = "주전급 5명" if i <= STARTER_COUNT else "벤치 핵심 4명"
            player_en = p.get("name_en") or p.get("name_jp") or ""
            player_en = canonical_player_en(player_en)
            rows.append([
                "",
                "",
                i,
                tier,
                player_en,
                p.get("name_korean") or lookup_player_ko(player_en, player_en_to_ko),
                p.get("games_started") or 0,
                avg_min_decimal(p),
            ])
    return rows


def parse_research_row(
    row: list,
    *,
    current_team: str = "",
    current_team_ko: str = "",
) -> dict | None:
    if not row:
        return None
    if is_header_row(row) or is_team_header_row(row):
        return None

    if len(row) >= RESEARCH_COLS:
        try:
            rank = int(float(row[2]))
        except (TypeError, ValueError):
            return None
        team_en = str(row[0]).strip() or current_team
        if not team_en:
            return None
        player_en = canonical_player_en(str(row[4]).strip())
        team_ko = str(row[1]).strip() if str(row[1]).strip() else current_team_ko
        return {
            "team": team_en,
            "team_ko": team_ko,
            "rank": rank,
            "tier": str(row[3]).strip() if len(row) > 3 else "",
            "player": player_en,
            "player_ko": str(row[5]).strip() if len(row) > 5 else "",
        }

    try:
        rank = int(float(row[1]))
    except (TypeError, ValueError):
        return None
    team_en = str(row[0]).strip() or current_team
    if not team_en:
        return None
    return {
        "team": team_en,
        "team_ko": current_team_ko,
        "rank": rank,
        "tier": str(row[2]).strip() if len(row) > 2 else "",
        "player": canonical_player_en(str(row[3]).strip()),
        "player_ko": "",
    }


def parse_sheet_rows(values: list[list]) -> dict[tuple[str, int], dict]:
    out: dict[tuple[str, int], dict] = {}
    current_team = ""
    current_team_ko = ""
    for row in values:
        if is_team_header_row(row):
            current_team = str(row[0]).strip()
            current_team_ko = str(row[1]).strip() if len(row) > 1 else ""
            continue
        parsed = parse_research_row(row, current_team=current_team, current_team_ko=current_team_ko)
        if not parsed:
            continue
        out[(norm_team(parsed["team"]), parsed["rank"])] = parsed
    return out


def get_sheets_creds(*, interactive: bool = False):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return None

    cred_path = ROOT / "gcp-oauth.keys.json"
    token_path = ROOT / "token.json"
    sheets_token_path = ROOT / "token-sheets.json"
    if not cred_path.is_file():
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    if sheets_token_path.is_file():
        with open(sheets_token_path, encoding="utf-8") as f:
            raw = json.load(f)
        with open(cred_path, encoding="utf-8") as f:
            client = json.load(f).get("installed") or {}
        creds = Credentials(
            token=raw.get("token") or raw.get("access_token") or "",
            refresh_token=raw.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client.get("client_id"),
            client_secret=client.get("client_secret"),
            scopes=scopes,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(sheets_token_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "token_uri": creds.token_uri,
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "scopes": list(creds.scopes or scopes),
                        "expiry": creds.expiry.isoformat() if creds.expiry else None,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        return creds

    if not interactive:
        raise RuntimeError(
            "Google Sheets 권한이 없습니다. "
            "python export_research_sheet.py --auth 로 한 번 인증한 뒤 --upload 를 실행하세요."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), scopes=scopes)
    creds = flow.run_local_server(port=0, open_browser=True)
    with open(sheets_token_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes or scopes),
                "expiry": creds.expiry.isoformat() if creds.expiry else None,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    return creds


def read_sheet_values(service, title: str) -> list[list]:
    resp = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{title}'!A:H",
    ).execute()
    return resp.get("values", [])


def upload_to_google(
    rows: list[list],
    sheet_title: str,
    *,
    service=None,
    formatted: bool = False,
) -> str:
    creds = get_sheets_creds(interactive=False)
    if creds is None:
        raise RuntimeError("Google OAuth 패키지 또는 gcp-oauth.keys.json 이 없습니다.")

    from googleapiclient.discovery import build

    if service is None:
        service = build("sheets", "v4", credentials=creds)
    if not formatted:
        rows = prepend_header(layout_with_team_headers(rows))
    elif rows and not is_header_row(rows[0]):
        rows = prepend_header(rows)
    meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    existing = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}
    if sheet_title not in existing:
        resp = service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]},
        ).execute()
        sheet_id = resp["replies"][0]["addSheet"]["properties"]["sheetId"]
    else:
        sheet_id = existing[sheet_title]

    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_title}'!A:H",
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_title}'!A1",
        valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()
    apply_research_formatting(service, sheet_id, rows)
    return f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid={sheet_id}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conference", choices=("west", "east"), default="west")
    parser.add_argument("--sheet-title", default="서부")
    parser.add_argument("--csv", type=Path, help="CSV 저장 경로 (선택)")
    parser.add_argument("--upload", action="store_true", help="Google Sheets에 업로드")
    parser.add_argument("--enrich-sheet", help="기존 시트에 한글 컬럼 추가 후 덮어쓰기")
    parser.add_argument("--sync-all", action="store_true", help="시트1·서부·동부비교 일괄 갱신")
    parser.add_argument("--auth", action="store_true", help="Google Sheets OAuth 인증")
    args = parser.parse_args()

    if args.sync_all:
        from compare_east_research import sync_compare_sheet

        creds = get_sheets_creds(interactive=False)
        if creds is None:
            print("Google Sheets 인증 필요", file=sys.stderr)
            return 1
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)
        with open(ROSTERS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        teams = data["teams"]
        team_en_to_ko, player_en_to_ko = build_roster_lookups(teams)

        west_rows = build_rows(teams, WEST_ORDER)
        url_w = upload_to_google(west_rows, "서부", service=service, formatted=True)
        print(f"서부 -> {url_w}")

        sheet1_raw = read_sheet_values(service, "시트1")
        sheet1_flat = enrich_legacy_rows(sheet1_raw, team_en_to_ko, player_en_to_ko)
        sheet1_rows = prepend_header(layout_with_team_headers(sheet1_flat))
        url_e = upload_to_google(sheet1_rows, "시트1", service=service, formatted=True)
        print(f"시트1 -> {url_e}")

        url_c = sync_compare_sheet(service, teams)
        print(f"동부 비교 -> {url_c}")
        return 0

    if args.enrich_sheet:
        creds = get_sheets_creds(interactive=False)
        if creds is None:
            print("Google Sheets 인증 필요", file=sys.stderr)
            return 1
        from googleapiclient.discovery import build

        service = build("sheets", "v4", credentials=creds)
        with open(ROSTERS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        team_en_to_ko, player_en_to_ko = build_roster_lookups(data["teams"])
        raw = read_sheet_values(service, args.enrich_sheet)
        rows = enrich_legacy_rows(raw, team_en_to_ko, player_en_to_ko)
        url = upload_to_google(rows, args.enrich_sheet)
        print(f"Enriched '{args.enrich_sheet}' -> {url}")
        return 0

    if args.auth:
        get_sheets_creds(interactive=True)
        print(f"인증 완료 -> {ROOT / 'token-sheets.json'}")
        return 0

    with open(ROSTERS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    teams = data["teams"]
    order = WEST_ORDER if args.conference == "west" else EAST_ORDER
    rows = build_rows(teams, order)
    rows = prepend_header(rows)

    print(f"{args.conference} {len(rows)} rows ({len(order)} teams x 9)")

    if args.csv:
        import csv
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        print(f"CSV -> {args.csv}")

    if args.upload:
        url = upload_to_google(rows, args.sheet_title)
        print(f"Uploaded sheet '{args.sheet_title}' -> {url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

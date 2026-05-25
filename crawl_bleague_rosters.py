#!/usr/bin/env python3
"""bleague.jp -> bleague-rosters.json (B.PREMIER east + west rosters, KO names, logos)."""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from datetime import date
from html import unescape
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

SEASON = "2025-26"
CDN = "https://bleague.bl.kuroco-img.app"
LOGO = f"{CDN}/files/user/common/img/logo/2025/m/{{code}}.png"

# id, teamId, logo_code, name_korean, primary, accent, conference
EAST_TEAMS = [
    ("levanga",      702,  "lh", "레반가 홋카이도",           "#006747", "#C8A951"),
    ("sendai",       692,  "se", "센다이 89ers",              "#F05A28", "#1A1A1A"),
    ("akita",        693,  "an", "아키타 노던 해피네츠",       "#E4007F", "#FFFFFF"),
    ("ibaraki",      712,  "ir", "이바라키 로봇츠",           "#0B2340", "#F5B800"),
    ("utsunomiya",   703,  "ub", "우츠노미야 브렉스",         "#FDB913", "#1A1A1A"),
    ("gunma",        713,  "gc", "군마 크레인 썬더스",         "#6EC4E8", "#2D2D2D"),
    ("altiri_chiba", 2486, "ac", "알티리 치바",               "#C8102E", "#FFFFFF"),
    ("chiba_jets",   704,  "cj", "치바 제츠",                 "#004B87", "#FDB913"),
    ("alvark_tokyo", 706,  "at", "알바르크 도쿄",             "#111111", "#FDB913"),
    ("sun_rockers",  726,  "sr", "선 로커스 시부야",           "#FF6B00", "#111111"),
    ("kawasaki",     727,  "kb", "가와사키 브레이브 썬더스",   "#003893", "#FDB913"),
    ("yokohama",     694,  "yb", "요코하마 B-코세ars",        "#002D62", "#C8102E"),
    ("koshigaya",    745,  "ka", "고시가야 알파스",            "#001489", "#FF6900"),
]

WEST_TEAMS = [
    ("shinshu",   716,  "bw", "신슈 브레이브워리어즈",     "#1B3FA0", "#E8B84B", "west"),
    ("sanen",     697,  "sn", "산엔 네오피닉스",           "#C41230", "#F5C518", "west"),
    ("mikawa",    728,  "sm", "시호스 미카와",             "#0A2550", "#D4A017", "west"),
    ("nagoya_dd", 729,  "dd", "나고야 다이아몬드 돌핀스",   "#003DA5", "#E8112D", "west"),
    ("shiga",     698,  "ls", "시가 레이크스",             "#0D6E64", "#FCD34D", "west"),
    ("kyoto",     699,  "kh", "교토 핸나리즈",             "#831843", "#FDE68A", "west"),
    ("osaka",     700,  "oe", "오사카 에베사",             "#C2410C", "#60A5FA", "west"),
    ("kobe",      718,  "ns", "고베 스토크스",             "#0D2137", "#00B4D8", "west"),
    ("shimane",   720,  "ss", "시마네 스사노오 매직",       "#5B21B6", "#DDD6FE", "west"),
    ("hiroshima", 721,  "hd", "히로시마 드래곤플라이즈",     "#991B1B", "#7DD3FC", "west"),
    ("saga",      1638, "sg", "사가 발루너스",             "#1A4BA3", "#FB923C", "west"),
    ("nagasaki",  2488, "nv", "나가사키 벨카",             "#1B3FA0", "#FFFFFF", "west"),
    ("ryukyu",    701,  "rg", "류큐 골든킹스",             "#003087", "#FFD700", "west"),
    ("toyama",    696,  "tg", "도야마 그라우지스",          "#FF6600", "#FFFFFF", "west"),
    ("fighting_eagles", 717, "fe", "파이팅 이글스 나고야",   "#003087", "#FFFFFF", "west"),
]

TEAMS = [
    *[(key, tid, logo, name, pri, acc, "east") for key, tid, logo, name, pri, acc in EAST_TEAMS],
    *WEST_TEAMS,
]

NAT_MAP = {
    "日本": "Japan",
    "アメリカ": "USA", "アメリカ合衆国": "USA", "米国": "USA",
    "韓国": "Korea", "大韓民国": "Korea",
    "オーストラリア": "Australia", "豪州": "Australia",
    "フランス": "France", "カナダ": "Canada", "台湾": "Taiwan",
    "ニュージーランド": "New Zealand", "リトアニア": "Lithuania",
    "セルビア": "Serbia", "モンテネグロ": "Montenegro", "クロアチア": "Croatia",
    "ブラジル": "Brazil", "ナイジェリア": "Nigeria", "フィリピン": "Philippines",
    "ドイツ": "Germany", "スペイン": "Spain", "イタリア": "Italy", "中国": "China",
    "プエルトリコ": "Puerto Rico", "パナマ": "Panama", "ベネズエラ": "Venezuela",
    "スロベニア": "Slovenia", "ポーランド": "Poland", "ジョージア": "Georgia",
    "イギリス": "UK", "英国": "UK", "メキシコ": "Mexico", "ギリシャ": "Greece",
}

NAT_RULES = [
    ("Japan", ("日本",)),
    ("Korea", ("大韓民国", "韓国")),
    ("USA", ("アメリカ", "米国")),
    ("Australia", ("オーストラリア", "豪州")),
    ("Philippines", ("フィリピン",)),
    ("France", ("フランス",)),
    ("Canada", ("カナダ",)),
    ("Taiwan", ("台湾",)),
    ("New Zealand", ("ニュージーランド",)),
    ("Lithuania", ("リトアニア",)),
    ("Serbia", ("セルビア",)),
    ("Montenegro", ("モンテネグロ",)),
    ("Croatia", ("クロアチア",)),
    ("Brazil", ("ブラジル",)),
    ("Nigeria", ("ナイジェリア",)),
    ("Germany", ("ドイツ",)),
    ("Spain", ("スペイン",)),
    ("Italy", ("イタリア",)),
    ("China", ("中国",)),
    ("Puerto Rico", ("プエルトリコ",)),
    ("Panama", ("パナマ",)),
    ("Venezuela", ("ベネズエラ",)),
    ("Slovenia", ("スロベニア",)),
    ("Poland", ("ポーランド",)),
    ("Georgia", ("ジョージア", "グルジア")),
    ("UK", ("イギリス", "英国")),
    ("Mexico", ("メキシコ",)),
    ("Argentina", ("アルゼンチン",)),
    ("Greece", ("ギリシャ",)),
    ("Finland", ("フィンランド",)),
    ("Senegal", ("セネガル",)),
    ("Bahamas", ("バハマ",)),
]


def map_nationality(nat_jp: str) -> str:
    nat_jp = (nat_jp or "").strip()
    if not nat_jp:
        return "Japan"
    if nat_jp in NAT_MAP:
        return NAT_MAP[nat_jp]
    for en, keys in NAT_RULES:
        if any(k in nat_jp for k in keys):
            return en
    if nat_jp.isascii():
        return nat_jp
    return "Japan"


def parse_nationality(html: str) -> str:
    nat_m = DETAIL_NAT.search(html)
    nat_jp = nat_m.group(1).strip() if nat_m else "日本"
    return map_nationality(nat_jp)

# 공식·언론 한글 표기 (build_korean_names.py가 갱신)
def load_name_overrides() -> dict[str, str]:
    path = Path(__file__).with_name("korean_name_overrides.json")
    if not path.exists():
        return {"51000379": "이현중"}
    return json.loads(path.read_text(encoding="utf-8"))


NAME_OVERRIDES: dict[str, str] = load_name_overrides()

from minutes_parser import parse_b1_minutes

DETAIL_EN = re.compile(
    r'class="first-name js-player-first-name">([^<]+)</span>\s*'
    r'<span class="last-name js-player-last-name">([^<]+)</span>'
)
DETAIL_NAT = re.compile(r"リーグ登録国籍</span><span>([^<]+)</span>")


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; bleague-crawler/2.0)"},
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        return res.read().decode("utf-8", errors="replace")


def normalize_photo(url: str, team_id: int, player_id: str) -> str:
    if url:
        url = unescape(re.sub(r"/v=\d+/", "/", url))
        if url.startswith("http"):
            return url
    return f"{CDN}/files/user/roster/{team_id}/{SEASON}/{player_id}_03.png"


def parse_position(raw: str) -> str:
    m = re.search(r"\b(PG|SG|SF|PF|C)\b", raw or "")
    return m.group(1) if m else "-"


def extract_players(html: str, team_id: int) -> dict[str, dict]:
    """Find players whose 2025-26 photo path matches this team."""
    found: dict[str, dict] = {}
    for m in re.finditer(
        rf"PlayerID=(\d+)[\s\S]{{0,5000}}?"
        rf"roster/{team_id}/{SEASON}/(\d+)_03\.png",
        html,
    ):
        pid, photo_pid = m.groups()
        if pid != photo_pid:
            continue
        chunk = html[m.start() : m.end() + 1200]
        num_m = re.search(r"playerInfo-player-num[^>]*>(\d+)</", chunk)
        photo_m = re.search(r'data-src="([^"]+)"', chunk)
        name_m = re.search(r'playerInfo-player-name">\s*([^<]+?)\s*<', chunk)
        pos_m = re.search(r"ポジション：<span>([^<]+)</span>", chunk)
        if not num_m:
            num_m = re.search(r"#(\d+)", pos_m.group(1) if pos_m else "")
        found[pid] = {
            "player_id": pid,
            "name_jp": unescape(name_m.group(1).strip()) if name_m else "",
            "number": num_m.group(1) if num_m else "",
            "position": parse_position(pos_m.group(1) if pos_m else ""),
            "photo_url": normalize_photo(
                photo_m.group(1) if photo_m else "", team_id, pid
            ),
            "profile_url": f"https://www.bleague.jp/roster_detail/?PlayerID={pid}",
        }
    return found


def fetch_player_detail(player_id: str) -> tuple[str, str, dict]:
    empty_mins = {
        "minutes_total": "",
        "minutes_avg": "",
        "minutes_total_sec": 0,
        "minutes_avg_sec": 0,
    }
    try:
        html = fetch(f"https://www.bleague.jp/roster_detail/?PlayerID={player_id}")
    except urllib.error.URLError:
        return "", "Japan", empty_mins
    en_m = DETAIL_EN.search(html)
    name_en = ""
    if en_m:
        name_en = f"{en_m.group(1).strip()} {en_m.group(2).strip()}".strip()
    nat_m = DETAIL_NAT.search(html)
    nat_jp = nat_m.group(1).strip() if nat_m else "日本"
    return (
        name_en,
        parse_nationality(html),
        parse_b1_minutes(html),
    )


def translate_to_ko(text: str, cache: dict[str, str], source: str = "en") -> str:
    text = (text or "").strip()
    if not text:
        return ""
    key = f"{source}:{text}"
    if key in cache:
        return cache[key]
    if GoogleTranslator is None:
        cache[key] = text
        return text
    try:
        ko = GoogleTranslator(source=source, target="ko").translate(text)
        cache[key] = ko or text
        time.sleep(0.12)
        return cache[key]
    except Exception:
        cache[key] = text
        return text


def korean_name(name_en: str, name_jp: str, cache: dict[str, str], player_id: str = "") -> str:
    if player_id in NAME_OVERRIDES:
        return NAME_OVERRIDES[player_id]
    if name_en:
        return translate_to_ko(name_en, cache, "en")
    if name_jp:
        return translate_to_ko(name_jp, cache, "ja")
    return ""


def merge_player_maps(base: dict[str, dict], extra: dict[str, dict]) -> None:
    for pid, p in extra.items():
        if pid not in base:
            base[pid] = p
            continue
        cur = base[pid]
        for key in ("name_jp", "number", "position", "photo_url"):
            if not cur.get(key) and p.get(key):
                cur[key] = p[key]


def crawl_team(key: str, team_id: int, logo_code: str, name_ko: str, primary: str, accent: str, conference: str, tr_cache: dict) -> dict:
    urls = [
        f"https://www.bleague.jp/club_detail/?TeamID={team_id}&tab=2",
        f"https://www.bleague.jp/mybleague_list/?TeamID={team_id}",
    ]
    merged: dict[str, dict] = {}
    for url in urls:
        try:
            html = fetch(url)
            merge_player_maps(merged, extract_players(html, team_id))
        except urllib.error.URLError as e:
            print(f"    WARN {url}: {e}", flush=True)

    players = []
    for pid, p in sorted(merged.items(), key=lambda x: int(x[1]["number"]) if x[1]["number"].isdigit() else 999):
        name_en, nationality, mins = fetch_player_detail(pid)
        name_korean = korean_name(name_en, p["name_jp"], tr_cache, pid)
        players.append({
            **p,
            **mins,
            "name_en": name_en,
            "name_korean": name_korean,
            "nationality": nationality,
        })
        time.sleep(0.25)

    return {
        "teamId": team_id,
        "conference": conference,
        "name_korean": name_ko,
        "logo_url": LOGO.format(code=logo_code),
        "primary": primary,
        "accent": accent,
        "players": players,
    }


WEST_KEYS = {t[0] for t in WEST_TEAMS}
EAST_KEYS = {t[0] for t in EAST_TEAMS}


def tag_conferences(teams: dict) -> None:
    for key, team in teams.items():
        if key in WEST_KEYS:
            team["conference"] = "west"
        elif key in EAST_KEYS:
            team["conference"] = "east"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--east", action="store_true", help="crawl east conference only")
    parser.add_argument("--west", action="store_true", help="crawl west conference only")
    args = parser.parse_args()

    if args.east and args.west:
        targets = TEAMS
    elif args.east:
        targets = [t for t in TEAMS if t[6] == "east"]
    elif args.west:
        targets = [t for t in TEAMS if t[6] == "west"]
    else:
        targets = TEAMS

    path = Path(__file__).with_name("bleague-rosters.json")
    if path.exists() and (args.east or args.west):
        out = json.loads(path.read_text(encoding="utf-8"))
        out["updated"] = date.today().isoformat()
        if "teams" not in out:
            out["teams"] = {}
    else:
        out = {
            "season": SEASON,
            "updated": date.today().isoformat(),
            "source": "bleague.jp club_detail tab=2 + mybleague_list + roster_detail",
            "teams": {},
        }

    tr_cache: dict[str, str] = {}
    for key, tid, logo, name_ko, primary, accent, conference in targets:
        print(f"crawl {key} ({tid}) [{conference}]...", flush=True)
        try:
            team = crawl_team(key, tid, logo, name_ko, primary, accent, conference, tr_cache)
            out["teams"][key] = team
            print(f"  -> {len(team['players'])} players", flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            out["teams"][key] = {
                "teamId": tid, "conference": conference, "name_korean": name_ko,
                "logo_url": LOGO.format(code=logo),
                "primary": primary, "accent": accent,
                "players": [], "error": str(e),
            }

    tag_conferences(out["teams"])
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(t.get("players", [])) for t in out["teams"].values())
    print(f"Wrote {path.name} - {total} players, {len(tr_cache)} name translations", flush=True)
    print("Refreshing Korean names...", flush=True)
    import build_korean_names as bkn

    bkn.main()


if __name__ == "__main__":
    main()

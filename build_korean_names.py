#!/usr/bin/env python3
"""Resolve Korean display names via wiki search + web-verified overrides + rules."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

ROOT = Path(__file__).parent
ROSTERS = ROOT / "bleague-rosters.json"
OVERRIDES = ROOT / "korean_name_overrides.json"

# Korean media / wiki verified (web search)
VERIFIED: dict[str, str] = {
    "51000379": "이현중",
    "51000528": "마이크 다움",
    "8843": "웨인 마셜",
    "5100000017": "츠치야 다이키",
    "987": "레이 파크스 주니어",  # Ray Parks Jr. - jumpball/o-imo Korean coverage
}

VERIFIED_EN: dict[str, str] = {
    "Hyunjung Lee": "이현중",
    "HyunjungLee": "이현중",
    "Mike Daum": "마이크 다움",
    "Wayne Marshall": "웨인 마셜",
    "Daiki Tsuchiya": "츠치야 다이키",
    "Ray Parks Jr.": "레이 파크스 주니어",
    "Ray Parks": "레이 파크스 주니어",
    "Stanley Johnson": "스탠리 존슨",
    "Jarell Brantley": "자렐 브랜틀리",
    "Matt Bonds": "맷 본즈",
    "Ryan Luther": "라이언 루서",
    "Vic Law": "빅 로",
    "Keve Aluma": "케베 알루마",
    "Eliet Donley": "엘리엇 돈리",
    "Louis Kurihara": "루이스 쿠리하라",
    "Akitoshi Oguri": "오구리 아키토시",
    "Taichi Kodama": "코다마 타이치",
}

KATAKANA = re.compile(r"[\u30a0-\u30ff\u31f0-\u31ff]")
KANJI = re.compile(r"[\u4e00-\u9fff]")
WIKI = "https://ko.wikipedia.org/w/api.php"


def fetch_json(url: str) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": "bleague-ko-names/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def wiki_ko_title(query: str) -> str:
    q = urllib.parse.urlencode({"action": "opensearch", "search": query, "limit": 3, "format": "json"})
    data = fetch_json(f"{WIKI}?{q}")
    if not data or len(data) < 2 or not data[1]:
        return ""
    for title in data[1]:
        if "농구" in title or re.search(r"^[가-힣]{2,8}(\s|$|\()", title):
            return re.sub(r"\s*\(.*\)$", "", title).strip()
    return ""


def translate(text: str, source: str, cache: dict[str, str]) -> str:
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
        out = GoogleTranslator(source=source, target="ko").translate(text) or text
        cache[key] = out.strip()
        time.sleep(0.1)
        return cache[key]
    except Exception:
        cache[key] = text
        return text


def split_en(name_en: str) -> list[str]:
    name_en = re.sub(r"\s+", " ", (name_en or "").strip())
    if not name_en:
        return []
    if " " not in name_en and re.search(r"[a-z][A-Z]", name_en):
        name_en = re.sub(r"([a-z])([A-Z])", r"\1 \2", name_en)
    parts = name_en.split(" ")
    if len(parts) >= 2 and parts[-1].lower() in {"jr.", "jr", "sr.", "sr", "ii", "iii"}:
        parts[-2] = f"{parts[-2]} {parts[-1]}"
        parts.pop()
    return parts


def resolve(player: dict, cache: dict[str, str]) -> str:
    pid = player["player_id"]
    if pid in VERIFIED:
        return VERIFIED[pid]

    name_en = (player.get("name_en") or "").strip()
    name_jp = (player.get("name_jp") or "").strip()
    nat = player.get("nationality") or "Japan"

    if name_en in VERIFIED_EN:
        return VERIFIED_EN[name_en]
    en_compact = name_en.replace(" ", "")
    if en_compact in VERIFIED_EN:
        return VERIFIED_EN[en_compact]

    if nat == "Korea":
        title = wiki_ko_title(f"{name_en} 농구") or wiki_ko_title(name_en)
        if title:
            return title

    if name_jp and (KATAKANA.search(name_jp) and not KANJI.search(name_jp.replace(" ", ""))):
        return translate(name_jp, "ja", cache)

    parts = split_en(name_en)
    if len(parts) >= 2:
        if nat == "Japan":
            family, given = parts[-1], " ".join(parts[:-1])
            ko_f = translate(family, "en", cache)
            ko_g = translate(given, "en", cache)
            return f"{ko_f} {ko_g}".strip()
        given, family = parts[0], " ".join(parts[1:])
        ko_g = translate(given, "en", cache)
        ko_f = translate(family, "en", cache)
        return f"{ko_g} {ko_f}".strip()

    if name_en:
        return translate(name_en, "en", cache)
    if name_jp:
        return translate(name_jp, "ja", cache)
    return ""


def main():
    data = json.loads(ROSTERS.read_text(encoding="utf-8"))
    cache: dict[str, str] = {}
    overrides: dict[str, str] = {}

    for team in data["teams"].values():
        for p in team["players"]:
            ko = resolve(p, cache)
            p["name_korean"] = ko
            overrides[p["player_id"]] = ko

    ROSTERS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OVERRIDES.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {len(overrides)} names -> {ROSTERS.name}, {OVERRIDES.name}")


if __name__ == "__main__":
    main()

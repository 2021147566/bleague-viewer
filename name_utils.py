"""English/Korean name normalization + unified aliases (name_aliases.json)."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_ALIASES_PATH = Path(__file__).with_name("name_aliases.json")

_SUFFIXES = frozenset({"jr", "sr", "ii", "iii"})


def strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def norm_name(name: str) -> str:
    s = strip_accents(name).strip().lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    parts = [p for p in s.split() if p and p not in _SUFFIXES]
    return "".join(sorted(parts))


@lru_cache(maxsize=1)
def _load_aliases() -> tuple[dict[str, str], dict[str, str]]:
    """Returns (player_norm->canonical_en, team_en->team_ko)."""
    if not _ALIASES_PATH.is_file():
        return {}, {}
    data = json.loads(_ALIASES_PATH.read_text(encoding="utf-8"))
    team_ko = {str(k): str(v) for k, v in (data.get("teams") or {}).items()}
    player_map: dict[str, str] = {}
    for alias, canonical in (data.get("players") or {}).items():
        alias = str(alias).strip()
        canonical = str(canonical).strip()
        if not alias or not canonical:
            continue
        player_map[norm_name(alias)] = canonical
        player_map[norm_name(canonical)] = canonical
    return player_map, team_ko


def canonical_player_en(name: str) -> str:
    if not name:
        return name
    player_map, _ = _load_aliases()
    return player_map.get(norm_name(name), name.strip())


def player_name_key(name: str) -> str:
    return norm_name(canonical_player_en(name))


def team_ko_extra() -> dict[str, str]:
    _, team_aliases = _load_aliases()
    return team_aliases


def merge_team_ko_maps(team_en_to_ko: dict[str, str]) -> dict[str, str]:
    merged = dict(team_en_to_ko)
    for en, ko in team_ko_extra().items():
        merged[_norm_team(en)] = ko
    return merged


def lookup_team_ko_from_maps(team_en: str, team_en_to_ko: dict[str, str]) -> str:
    extras = team_ko_extra()
    if team_en in extras:
        return extras[team_en]
    return team_en_to_ko.get(_norm_team(team_en), "")


def _norm_team(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())

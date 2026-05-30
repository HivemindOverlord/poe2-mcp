"""
Canonical paths for extracted PoE2 game data tracked in this repo.

Use these constants instead of hardcoding strings — the layout can move and
callers won't notice:

    from src.data.game_data import MODS_JSON, PASSIVE_TREE_JSON, load_mods
    mods = load_mods()

See `data/game/README.md` for the layout, lifecycle, and data policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
GAME_DATA_DIR = _BASE_DIR / "data" / "game"

# Global version manifest
VERSION_JSON = GAME_DATA_DIR / "version.json"

# Datasets — each is its own folder with `<name>.json` + `metadata.json`
MODS_DIR = GAME_DATA_DIR / "mods"
MODS_JSON = MODS_DIR / "mods.json"
MODS_META = MODS_DIR / "metadata.json"

PASSIVE_TREE_DIR = GAME_DATA_DIR / "passive_tree"
PASSIVE_TREE_JSON = PASSIVE_TREE_DIR / "tree.json"
PASSIVE_TREE_META = PASSIVE_TREE_DIR / "metadata.json"

SUPPORT_GEMS_DIR = GAME_DATA_DIR / "support_gems"
SUPPORT_GEMS_JSON = SUPPORT_GEMS_DIR / "support_gems.json"
SUPPORT_GEMS_META = SUPPORT_GEMS_DIR / "metadata.json"

ASCENDANCIES_DIR = GAME_DATA_DIR / "ascendancies"
ASCENDANCIES_JSON = ASCENDANCIES_DIR / "ascendancies.json"
ASCENDANCIES_META = ASCENDANCIES_DIR / "metadata.json"

STATS_DIR = GAME_DATA_DIR / "stats"
STATS_JSON = STATS_DIR / "stats.json"
STATS_META = STATS_DIR / "metadata.json"

# Datasets pending 0.5 re-extract (paths reserved; folders may not yet exist).
SKILL_GEMS_DIR = GAME_DATA_DIR / "skill_gems"


def get_version() -> Optional[Dict[str, Any]]:
    """Return the parsed contents of data/game/version.json, or None if missing."""
    if not VERSION_JSON.exists():
        return None
    try:
        return json.loads(VERSION_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_mods() -> Optional[Dict[str, Any]]:
    """Load and return the canonical mods dataset, or None if missing."""
    if not MODS_JSON.exists():
        return None
    return json.loads(MODS_JSON.read_text(encoding="utf-8"))


def load_passive_tree() -> Optional[Dict[str, Any]]:
    """Load and return the canonical passive tree dataset, or None if missing."""
    if not PASSIVE_TREE_JSON.exists():
        return None
    return json.loads(PASSIVE_TREE_JSON.read_text(encoding="utf-8"))


def load_support_gems() -> Optional[Dict[str, Any]]:
    """Load and return the canonical support gems dataset, or None if missing."""
    if not SUPPORT_GEMS_JSON.exists():
        return None
    return json.loads(SUPPORT_GEMS_JSON.read_text(encoding="utf-8"))


def load_ascendancies() -> Optional[Dict[str, Any]]:
    """Load and return the canonical ascendancies dataset, or None if missing."""
    if not ASCENDANCIES_JSON.exists():
        return None
    return json.loads(ASCENDANCIES_JSON.read_text(encoding="utf-8"))


def load_stats() -> Optional[Dict[int, str]]:
    """Load and return the canonical stats table as a {row_index: stat_id} dict.

    Returns the dict form (not the raw JSON envelope) because that's the shape
    every caller wants — for resolving stat_key references from mods, passives,
    and gems. Returns None if stats.json is missing.
    """
    if not STATS_JSON.exists():
        return None
    payload = json.loads(STATS_JSON.read_text(encoding="utf-8"))
    return {entry["row_index"]: entry["stat_id"] for entry in payload.get("stats", [])}


def load_metadata(dataset_dir: Path) -> Optional[Dict[str, Any]]:
    """Load `metadata.json` from a dataset directory."""
    meta = dataset_dir / "metadata.json"
    if not meta.exists():
        return None
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def describe() -> str:
    """Human-readable summary of what data is currently installed. Useful for
    health_check / diagnostic output."""
    v = get_version()
    if not v:
        return "data/game/ not populated yet — see README.md"
    lines = [
        f"PoE2 Patch {v.get('patch_version', '?')} "
        f"({v.get('patch_name', '?')}, released {v.get('patch_released', '?')})",
        f"Released as: {v.get('released_as', '?')}; data revision {v.get('data_revision', '?')}",
        f"Extracted: {v.get('extracted_at', '?')}",
    ]
    for ds, info in (v.get("datasets") or {}).items():
        lines.append(f"  - {ds}: {info.get('record_count', '?')} records at {info.get('path', '?')}")
    pending = v.get("datasets_pending_0_5_reextract") or {}
    if pending:
        lines.append(f"  pending re-extract: {', '.join(pending.keys())}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe())

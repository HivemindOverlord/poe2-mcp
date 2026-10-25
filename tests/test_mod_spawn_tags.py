"""
Tests for the mod SpawnTags / item-class filtering feature (Bug 3, 2026-06-16).

Two layers:
  - src/mod_data.py loaders (load_spawn_tags, available_spawn_tags,
    normalize_item_class) — exercised against a synthetic data dir so they pass
    without the real game data.
  - get_available_mods handler `item_class` filtering — skipped when the real
    data/game/mods/spawn_tags.json is absent (older checkout / no data release).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import pytest_asyncio

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src import mod_data

# ---------------------------------------------------------------------------
# mod_data loaders (synthetic data dir)
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_data_dir(tmp_path):
    """A data dir with a minimal spawn_tags.json."""
    mods_dir = tmp_path / "game" / "mods"
    mods_dir.mkdir(parents=True)
    payload = {
        "metadata": {"dataset": "mod_spawn_tags"},
        "spawn_tags": {
            "IncreasedMana1": ["ring", "wand", "sceptre", "default"],
            "Strength1": ["ring", "amulet", "mace", "sceptre", "default"],
            "SpellDamageOnWeapon1": ["wand", "staff", "sceptre"],
        },
    }
    (mods_dir / "spawn_tags.json").write_text(json.dumps(payload), encoding="utf-8")
    # Clear the module cache so a previous test's data dir doesn't leak.
    mod_data._SPAWN_TAGS_CACHE.clear()
    return tmp_path


def test_load_spawn_tags_reads_map(fake_data_dir):
    st = mod_data.load_spawn_tags(fake_data_dir)
    assert st["IncreasedMana1"] == ["ring", "wand", "sceptre", "default"]
    assert "wand" in st["SpellDamageOnWeapon1"]


def test_load_spawn_tags_missing_file_returns_empty(tmp_path):
    mod_data._SPAWN_TAGS_CACHE.clear()
    assert mod_data.load_spawn_tags(tmp_path) == {}


def test_available_spawn_tags_is_sorted_union(fake_data_dir):
    tags = mod_data.available_spawn_tags(fake_data_dir)
    assert tags == sorted(tags)
    assert "wand" in tags and "amulet" in tags and "staff" in tags


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Wand", "wand"),
        ("Body Armour", "body_armour"),
        ("  Ring  ", "ring"),
        ("one-hand-sword", "one_hand_sword"),
    ],
)
def test_normalize_item_class(raw, expected):
    assert mod_data.normalize_item_class(raw) == expected


# ---------------------------------------------------------------------------
# get_available_mods handler — real-data integration
# ---------------------------------------------------------------------------

REAL_SPAWN_TAGS = PROJECT_ROOT / "data" / "game" / "mods" / "spawn_tags.json"
_HAS_DATA = REAL_SPAWN_TAGS.exists()


@pytest_asyncio.fixture(scope="module")
async def mcp():
    from src.mcp_server import PoE2BuildOptimizerMCP

    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()
    return instance


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DATA, reason="spawn_tags.json not present")
async def test_get_available_mods_filters_by_wand(mcp):
    r = await mcp._handle_get_available_mods(
        {"generation_type": "PREFIX", "item_class": "Wand", "limit": 50}
    )
    text = r[0].text
    assert "Item class filter" in text and "wand" in text
    # Spell/elemental damage prefixes are the signature wand rolls.
    assert "SpellDamageOnWeapon" in text or "DamagePrefixOnWeapon" in text


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DATA, reason="spawn_tags.json not present")
async def test_get_available_mods_excludes_wrong_class(mcp):
    """A flat-strength mod rolls on armour/jewellery, never wands — it must not
    appear in the wand-filtered prefix list."""
    r = await mcp._handle_get_available_mods(
        {"generation_type": "PREFIX", "item_class": "Wand", "limit": 200}
    )
    assert "### Strength\n" not in r[0].text


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DATA, reason="spawn_tags.json not present")
async def test_get_available_mods_unknown_class_suggests(mcp):
    r = await mcp._handle_get_available_mods(
        {"generation_type": "PREFIX", "item_class": "NotAnItem"}
    )
    text = r[0].text
    assert "unknown item_class" in text.lower()
    assert "wand" in text  # suggestion list includes real tags


@pytest.mark.asyncio
@pytest.mark.skipif(not _HAS_DATA, reason="spawn_tags.json not present")
async def test_get_available_mods_no_filter_unchanged(mcp):
    """Without item_class the tool behaves as before (all item types)."""
    r = await mcp._handle_get_available_mods({"generation_type": "SUFFIX", "limit": 5})
    text = r[0].text
    assert "Item class filter" not in text
    assert "Available SUFFIX Mods" in text

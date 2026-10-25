"""
Tests for the canonical base-items load path added to fresh_data_provider (#205).

Background: FreshDataProvider never had a working source for base items.
`_extract_base_items()` (the raw .datc64 fallback) pointed at a stale path
missing the balance/ subdirectory AND was never reachable in practice because
`_load_from_complete_models()` short-circuits before Priority-3 raw extraction
ever runs on any install that ships the standard complete_models/ files —
i.e. every packaged install. list_all_base_items / inspect_base_item always
returned empty.

This suite locks the fix: data/game/base_items/base_items.json (extracted
from baseitemtypes.datc64 + itemclasses.datc64) loads unconditionally at the
start of _load_all_data(), independent of the complete_models short-circuit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fresh_data_provider import (  # noqa: E402
    BASE_ITEMS_CANONICAL,
    FreshDataProvider,
)


@pytest.fixture(scope="module")
def provider():
    """Force a clean reload of the singleton so the new code path runs."""
    FreshDataProvider._instance = None
    FreshDataProvider._initialized = False
    return FreshDataProvider()


def test_canonical_path_exists():
    assert BASE_ITEMS_CANONICAL.exists(), (
        f"Canonical base-items file missing: {BASE_ITEMS_CANONICAL}. "
        "If you intentionally removed it, this whole PR's premise is broken."
    )


def test_base_items_loaded_and_nonempty(provider):
    """The headline #205 bug: base items must not be empty."""
    items = provider.get_all_base_items()
    assert len(items) > 5000, (
        f"Expected 5000+ base items from canonical extraction, got {len(items)}. "
        "get_all_base_items() being near-empty is exactly the #205 bug."
    )


def test_known_weapon_base_present(provider):
    """Dull Hatchet: the first One Hand Axe base, used to reverse-engineer
    and validate the extraction schema (id@0, item_class FK@8, name@32)."""
    item = provider.get_base_item(
        "Metadata/Items/Weapons/OneHandWeapons/OneHandAxes/FourOneHandAxe1"
    )
    assert item is not None
    assert item["name"] == "Dull Hatchet"
    assert item["item_class"] == "One Hand Axe"


def test_known_currency_base_present(provider):
    item = provider.get_base_item("Metadata/Items/Currency/CurrencyRerollRare")
    assert item is not None
    assert item["name"] == "Chaos Orb"
    assert item["item_class"] == "StackableCurrency"


def test_dnt_rows_excluded(provider):
    """Rows the game data itself flags '[DNT]' (not visible to players, e.g.
    scaled Incursion currency variants) must not appear — they're internal-only
    and would be confusing garbage in a player-facing tool."""
    items = provider.get_all_base_items()
    dnt_names = [v.get("name", "") for v in items.values() if v.get("name", "").startswith("[DNT]")]
    assert dnt_names == [], f"DNT rows leaked into canonical output: {dnt_names[:5]}"


def test_item_class_name_is_human_readable(provider):
    """item_class carries the raw GGG id (e.g. 'One Hand Axe'); item_class_name
    carries the pluralized display form (e.g. 'One Hand Axes') for UI use."""
    item = provider.get_base_item(
        "Metadata/Items/Weapons/OneHandWeapons/OneHandAxes/FourOneHandAxe1"
    )
    assert item is not None
    assert item["item_class_name"] == "One Hand Axes"

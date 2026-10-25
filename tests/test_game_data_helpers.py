"""
Tests for the convenience-lookup helpers in src/data/game_data.py.

PR #80 added six lookup helpers on top of the base loaders already covered
by tests/test_game_data.py:
    - find_ascendancies_by_base_class
    - find_mods_by_stat_id
    - find_mods_by_display_name
    - get_keystones
    - get_notables
    - find_keystone_by_name

This file covers them. Approach matches tests/test_game_data.py — shape +
real-data sanity checks against the current data/game/ dataset, no synthetic
fixtures (these helpers are thin wrappers over loaded JSON and shape changes
should be caught by the same tests).
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.game_data import (
    find_ascendancies_by_base_class,
    find_keystone_by_name,
    find_mods_by_display_name,
    find_mods_by_stat_id,
    get_keystones,
    get_notables,
)

# ---------------------------------------------------------------------------
# find_ascendancies_by_base_class
# ---------------------------------------------------------------------------


def test_find_ascendancies_by_base_class_witch_returns_four():
    """Witch is documented as having 4 ascendancies (Infernalist, Blood Mage,
    Lich, Abyssal Lich) — the canonical example in the helper's docstring."""
    result = find_ascendancies_by_base_class("Witch")
    assert isinstance(result, list)
    names = sorted(a.get("display_name") for a in result)
    assert names == sorted(["Infernalist", "Blood Mage", "Lich", "Abyssal Lich"])


def test_find_ascendancies_by_base_class_case_insensitive():
    upper = find_ascendancies_by_base_class("WITCH")
    lower = find_ascendancies_by_base_class("witch")
    canonical = find_ascendancies_by_base_class("Witch")
    assert {a["id"] for a in upper} == {a["id"] for a in lower} == {a["id"] for a in canonical}


def test_find_ascendancies_by_base_class_unknown_returns_empty():
    """Garbage input returns []; never raises."""
    assert find_ascendancies_by_base_class("NotAClass") == []
    assert find_ascendancies_by_base_class("") == []


def test_find_ascendancies_by_base_class_excludes_unused_by_default():
    """include_unused defaults False — verify no DNT-UNUSED placeholders leak
    into normal lookups."""
    result = find_ascendancies_by_base_class("Witch")
    for entry in result:
        assert not entry.get(
            "is_unused"
        ), f"Unused entry leaked into default lookup: {entry.get('id')}"


def test_find_ascendancies_by_base_class_each_entry_has_required_fields():
    result = find_ascendancies_by_base_class("Witch")
    assert result, "Witch should have at least one ascendancy"
    for entry in result:
        assert "id" in entry
        assert "display_name" in entry
        assert (entry.get("base_class") or "").lower() == "witch"


# ---------------------------------------------------------------------------
# find_mods_by_stat_id
# ---------------------------------------------------------------------------


def test_find_mods_by_stat_id_returns_real_strength_mods():
    """additional_strength is a stat that appears on many mods — non-empty result."""
    result = find_mods_by_stat_id("additional_strength")
    assert isinstance(result, list)
    assert len(result) > 0, "expected at least one mod granting additional_strength"


def test_find_mods_by_stat_id_case_insensitive():
    upper = find_mods_by_stat_id("ADDITIONAL_STRENGTH")
    lower = find_mods_by_stat_id("additional_strength")
    # Same set of mods regardless of case
    assert {m.get("mod_id") for m in upper} == {m.get("mod_id") for m in lower}


def test_find_mods_by_stat_id_respects_limit():
    """Default limit is 50 — high-frequency stats should be capped."""
    result = find_mods_by_stat_id("additional_strength")
    assert len(result) <= 50

    smaller = find_mods_by_stat_id("additional_strength", limit=5)
    assert len(smaller) <= 5


def test_find_mods_by_stat_id_sorted_by_level_ascending():
    """Helper sorts by level_requirement asc — lowest tier first."""
    result = find_mods_by_stat_id("additional_strength", limit=20)
    levels = [m.get("level_requirement", 0) for m in result]
    assert levels == sorted(levels), f"results not sorted by level_requirement: {levels}"


def test_find_mods_by_stat_id_generation_type_filter():
    """generation_type filter narrows results to that type only."""
    prefix_mods = find_mods_by_stat_id("additional_strength", generation_type="PREFIX")
    suffix_mods = find_mods_by_stat_id("additional_strength", generation_type="SUFFIX")

    for mod in prefix_mods:
        assert mod.get("generation_type_name") == "PREFIX"
    for mod in suffix_mods:
        assert mod.get("generation_type_name") == "SUFFIX"


def test_find_mods_by_stat_id_unknown_stat_returns_empty():
    assert find_mods_by_stat_id("definitely_not_a_real_stat_id_12345") == []


# ---------------------------------------------------------------------------
# find_mods_by_display_name
# ---------------------------------------------------------------------------


def test_find_mods_by_display_name_returns_known_suffix():
    """'of the Newt' is a canonical low-level life suffix — expect hits."""
    result = find_mods_by_display_name("of the Newt")
    assert len(result) > 0, "expected at least one mod with 'of the Newt' display_name"


def test_find_mods_by_display_name_case_insensitive():
    upper = find_mods_by_display_name("OF THE NEWT")
    lower = find_mods_by_display_name("of the newt")
    assert {m.get("mod_id") for m in upper} == {m.get("mod_id") for m in lower}


def test_find_mods_by_display_name_substring_match():
    """Helper uses substring (not exact) match — 'Newt' alone should also hit."""
    result = find_mods_by_display_name("Newt")
    assert len(result) > 0


def test_find_mods_by_display_name_unknown_returns_empty():
    assert find_mods_by_display_name("zzzzzzz_not_a_real_mod_name_zzzzzzz") == []


def test_find_mods_by_display_name_respects_limit():
    result = find_mods_by_display_name("of the Newt", limit=3)
    assert len(result) <= 3


def test_find_mods_by_display_name_sorted_by_level_ascending():
    result = find_mods_by_display_name("of the Newt", limit=20)
    levels = [m.get("level_requirement", 0) for m in result]
    assert levels == sorted(levels)


# ---------------------------------------------------------------------------
# get_keystones / get_notables
# ---------------------------------------------------------------------------


def test_get_keystones_returns_nonempty_list():
    """Per version.json the tree has 82 keystones in 0.5 — must not return zero."""
    kstones = get_keystones()
    assert isinstance(kstones, list)
    assert len(kstones) > 0


def test_get_keystones_every_entry_is_keystone():
    for k in get_keystones():
        assert k.get("is_keystone") is True


def test_get_notables_returns_nonempty_list():
    """Per version.json the tree has 2,151 notables in 0.5 — must not return zero."""
    notables = get_notables()
    assert isinstance(notables, list)
    assert len(notables) > 0


def test_get_notables_excludes_keystones():
    """Notables and keystones are disjoint per the helper's filter."""
    for n in get_notables():
        assert n.get("is_notable") is True
        assert not n.get(
            "is_keystone"
        ), f"Keystone leaked into notables: {n.get('name')} ({n.get('id')})"


def test_get_keystones_and_notables_are_disjoint():
    """No node should appear in both lists."""
    keystone_ids = {k.get("id") for k in get_keystones()}
    notable_ids = {n.get("id") for n in get_notables()}
    assert keystone_ids.isdisjoint(notable_ids)


# ---------------------------------------------------------------------------
# find_keystone_by_name
# ---------------------------------------------------------------------------


def test_find_keystone_by_name_exact_match():
    """Docstring example: Resolute Technique."""
    result = find_keystone_by_name("Resolute Technique")
    assert result is not None
    assert result.get("name") == "Resolute Technique"
    assert result.get("is_keystone") is True


def test_find_keystone_by_name_case_insensitive():
    upper = find_keystone_by_name("RESOLUTE TECHNIQUE")
    lower = find_keystone_by_name("resolute technique")
    mixed = find_keystone_by_name("Resolute Technique")
    assert upper is not None and lower is not None and mixed is not None
    assert upper.get("id") == lower.get("id") == mixed.get("id")


def test_find_keystone_by_name_strips_whitespace():
    """Helper docstring promises case-insensitive + stripped — verify both."""
    padded = find_keystone_by_name("  Resolute Technique  ")
    direct = find_keystone_by_name("Resolute Technique")
    assert padded is not None
    assert padded.get("id") == direct.get("id")


def test_find_keystone_by_name_unknown_returns_none():
    """Not found returns None (not empty dict, not raise)."""
    assert find_keystone_by_name("This Keystone Does Not Exist Anywhere") is None

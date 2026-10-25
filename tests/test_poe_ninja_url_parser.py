"""
Tests for poe.ninja profile/builds URL parsing (field feedback, 2026-06-11).

The 0.5 poe.ninja site links characters as
``/poe2/profile/{account}/{league}/character/{char}`` — the old parser in
``_handle_import_poe_ninja_url`` only knew the league-less form and rejected
real URLs, then hardcoded league="Vaal" on the ones it did accept. The parse
logic now lives in ``src.api.poe_ninja_api.parse_poe_ninja_url`` so it's unit
testable without booting the MCP server.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.poe_ninja_api import league_slug_to_display, parse_poe_ninja_url

# ---------------------------------------------------------------------------
# URL shapes
# ---------------------------------------------------------------------------


def test_profile_url_with_league_segment():
    """The real 0.5 format — the exact shape the old parser rejected."""
    parsed = parse_poe_ninja_url(
        "https://poe.ninja/poe2/profile/Tomawar40-2671/runesofaldur/character/TomawarTheFourth"
    )
    assert parsed is not None
    assert parsed["account"] == "Tomawar40-2671"
    assert parsed["character"] == "TomawarTheFourth"
    assert parsed["league_slug"] == "runesofaldur"
    assert parsed["league"] == "Runes of Aldur"


def test_profile_url_without_league_segment():
    """Pre-0.5 / league-less form still parses; league comes back None."""
    parsed = parse_poe_ninja_url(
        "https://poe.ninja/poe2/profile/Tomawar40-2671/character/TomawarTheFourth"
    )
    assert parsed is not None
    assert parsed["account"] == "Tomawar40-2671"
    assert parsed["character"] == "TomawarTheFourth"
    assert parsed["league_slug"] is None
    assert parsed["league"] is None


def test_builds_url_with_league_segment():
    parsed = parse_poe_ninja_url(
        "https://poe.ninja/poe2/builds/runesofaldurhc/character/SomeAcct/SomeChar"
    )
    assert parsed is not None
    assert parsed["account"] == "SomeAcct"
    assert parsed["character"] == "SomeChar"
    assert parsed["league"] == "Runes of Aldur Hardcore"


def test_builds_url_legacy_no_league():
    parsed = parse_poe_ninja_url("https://poe.ninja/poe2/builds/character/SomeAcct/SomeChar")
    assert parsed is not None
    assert parsed["account"] == "SomeAcct"
    assert parsed["character"] == "SomeChar"
    assert parsed["league_slug"] is None


def test_poe1_style_builds_url():
    parsed = parse_poe_ninja_url("https://poe.ninja/builds/character/SomeAcct/SomeChar")
    assert parsed is not None
    assert parsed["account"] == "SomeAcct"
    assert parsed["character"] == "SomeChar"


def test_url_with_query_string():
    """Query params must not bleed into the character name."""
    parsed = parse_poe_ninja_url(
        "https://poe.ninja/poe2/profile/Acct/vaal/character/Char?timemachine=week-1"
    )
    assert parsed is not None
    assert parsed["character"] == "Char"
    assert parsed["league"] == "Fate of the Vaal"


def test_percent_encoded_account():
    """Discriminators sometimes arrive percent-encoded (# -> %23)."""
    parsed = parse_poe_ninja_url(
        "https://poe.ninja/poe2/profile/Acct%231234/runesofaldur/character/Char"
    )
    assert parsed is not None
    assert parsed["account"] == "Acct#1234"


def test_unknown_league_slug_passes_through():
    """Future leagues we haven't mapped yet keep the raw slug available."""
    parsed = parse_poe_ninja_url("https://poe.ninja/poe2/profile/Acct/futureleague/character/Char")
    assert parsed is not None
    assert parsed["league_slug"] == "futureleague"
    assert parsed["league"] is None


def test_garbage_url_returns_none():
    assert parse_poe_ninja_url("https://example.com/not/poe/ninja") is None
    assert parse_poe_ninja_url("") is None


# ---------------------------------------------------------------------------
# Slug reverse-mapping
# ---------------------------------------------------------------------------


def test_slug_reverse_mapping_prefers_canonical_name():
    """First LEAGUE_MAPPINGS entry per slug is the canonical display name."""
    assert league_slug_to_display("runesofaldur") == "Runes of Aldur"
    assert league_slug_to_display("runesofaldurhcssf") == "Runes of Aldur HC SSF"
    assert league_slug_to_display("vaal") == "Fate of the Vaal"
    assert league_slug_to_display("abyss") == "Rise of the Abyssal"


def test_slug_reverse_mapping_unknown_and_empty():
    assert league_slug_to_display("nosuchleague") is None
    assert league_slug_to_display(None) is None
    assert league_slug_to_display("") is None

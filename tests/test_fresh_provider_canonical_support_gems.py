"""
Tests for the canonical support-gems load path added to fresh_data_provider.

Background: prior to this PR, FreshDataProvider loaded support gems exclusively
from data/complete_models/support_gems.json (551 entries, pre-Patch-0.5). The
post-0.5 .datc64-extracted canonical dataset at
data/game/support_gems/support_gems.json (680 entries) was ignored — so
inspect_support_gem("Wildfire") returned "not found" even though Wildfire is
present in the canonical extraction.

This suite locks the fix:
  1. Canonical file is preferred when present.
  2. Schema translation ('name' -> 'display_name') happens on load so existing
     lookups keep working.
  3. Lookups by name find post-0.5 additions (Wildfire) AND pre-0.5 entries
     that existed under both schemas (Wildshards) — no regressions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data.fresh_data_provider import (  # noqa: E402
    SUPPORT_GEMS_CANONICAL,
    FreshDataProvider,
)


@pytest.fixture(scope="module")
def provider():
    """Force a clean reload of the singleton so the new code path runs."""
    FreshDataProvider._instance = None
    FreshDataProvider._initialized = False
    return FreshDataProvider()


# ---------------------------------------------------------------------------
# Path + load-source preconditions
# ---------------------------------------------------------------------------


def test_canonical_path_exists():
    """The canonical extracted file must be present in the repo."""
    assert SUPPORT_GEMS_CANONICAL.exists(), (
        f"Canonical support-gems file missing: {SUPPORT_GEMS_CANONICAL}. "
        "If you intentionally removed it, this whole PR's premise is broken."
    )


def test_load_count_matches_canonical(provider):
    """Loaded gem count must equal canonical file's record count, not the
    smaller complete_models count. 680 is the post-Patch-0.5 number; the
    pre-0.5 file had 551."""
    assert len(provider._support_gems) == 680, (
        f"Expected 680 support gems from canonical file, got "
        f"{len(provider._support_gems)} — fresh_provider may still be reading "
        "the stale complete_models source."
    )


# ---------------------------------------------------------------------------
# Wildfire (the headline fix)
# ---------------------------------------------------------------------------


def test_wildfire_present_by_id(provider):
    """Wildfire is present in canonical extraction under SupportWildfirePlayer."""
    wf = provider.get_support_gem("SupportWildfirePlayer")
    assert wf is not None, (
        "SupportWildfirePlayer not loaded. This is the exact bug the PR "
        "exists to fix — re-check the canonical loader wiring."
    )
    assert wf.get("name") == "Wildfire Support"
    assert wf.get("is_support") is True


def test_wildfire_by_short_name(provider):
    """get_support_gem_by_name resolves the user-typed bare name."""
    wf = provider.get_support_gem_by_name("Wildfire")
    assert wf is not None
    assert wf.get("id") == "SupportWildfirePlayer"


def test_wildfire_by_full_name(provider):
    """get_support_gem_by_name resolves the full 'X Support' form."""
    wf = provider.get_support_gem_by_name("Wildfire Support")
    assert wf is not None
    assert wf.get("id") == "SupportWildfirePlayer"


def test_wildfire_display_name_mirrored(provider):
    """Schema-translation contract: canonical 'name' is mirrored to
    'display_name' on load, so legacy callers that read display_name
    keep working without modification."""
    wf = provider.get_support_gem("SupportWildfirePlayer")
    assert wf is not None
    assert wf.get("display_name") == wf.get("name") == "Wildfire Support"


# ---------------------------------------------------------------------------
# Regression: pre-0.5 gems still resolve
# ---------------------------------------------------------------------------


def test_wildshards_still_resolves(provider):
    """Wildshards existed in BOTH complete_models AND the canonical extraction.
    It must keep resolving after the switch."""
    ws = provider.get_support_gem_by_name("Wildshards")
    assert ws is not None
    assert ws.get("id") == "SupportWildshardsPlayer"


def test_tempestuous_tempo_still_resolves(provider):
    """Spot-check another support gem that existed in both complete_models
    and the canonical extraction. Tempestuous Tempo is a stable, established
    PoE2 support — if this stops resolving, the regression surface broke."""
    tt = provider.get_support_gem_by_name("Tempestuous Tempo")
    assert tt is not None
    assert "TempestuousTempo" in tt.get("id", "")


# ---------------------------------------------------------------------------
# Search surface
# ---------------------------------------------------------------------------


def test_search_finds_wildfire(provider):
    """Substring search surfaces Wildfire under 'wild' query."""
    results = provider.search_support_gems("wild")
    names = {r.get("display_name") or r.get("name") for r in results}
    assert (
        "Wildfire Support" in names
    ), f"search('wild') failed to surface Wildfire. Got: {sorted(names)}"
    # Sanity: also returns Wildshards variants
    assert any("Wildshards" in n for n in names if n)

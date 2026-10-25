"""
Tests for issue #133 — snapshot-endpoint retirement + profile-API
character enumeration.

The pre-0.5 snapshot endpoint (/poe2/api/builds/{version}/character) and
the HTML-scrape fallback are dead; both chains were deleted. The profile
API (account SSE -> char list; char SSE -> model) is the only fetch path.
All network calls are stubbed — shapes mirror the 2026-06-02 HAR capture,
re-verified live 2026-06-12.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.poe_ninja_api import PoeNinjaAPI

CHAR_LIST = [
    {
        "name": "TomawarTheSeventh",
        "level": 87,
        "className": "Infernalist",
        "league": "Runes of Aldur",
        "leagueUrl": "runesofaldur",
        "isCurrent": True,
    },
    {
        "name": "TomawarTheFifth",
        "level": 91,
        "className": "Shaman",
        "league": "Fate of the Vaal",
        "leagueUrl": "vaal",
        "isCurrent": False,
    },
]


class _FakeStreamResponse:
    def __init__(self, status_code=200, lines=()):
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeJsonResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeClient:
    """Routes profile-API URLs to canned responses; records what was hit."""

    def __init__(self):
        self.requested = []
        self.sse_lines = ['data: {"version":4197557768}']
        self.list_payload = CHAR_LIST
        self.model_payload = {
            "type": "full",
            "charModel": {"name": "TomawarTheSeventh", "pathOfBuildingExport": "eNrFAKEEXPORT"},
        }
        self.sse_status = 200
        self.list_status = 200

    def stream(self, _method, url):
        self.requested.append(url)
        return _FakeStreamResponse(self.sse_status, self.sse_lines)

    async def get(self, url, **kwargs):
        self.requested.append(url)
        if "/model/" in url:
            return _FakeJsonResponse(200, self.model_payload)
        return _FakeJsonResponse(self.list_status, self.list_payload)


class _FakeRateLimiter:
    async def acquire(self):
        return None


def _api() -> PoeNinjaAPI:
    api = PoeNinjaAPI.__new__(PoeNinjaAPI)
    api.base_url = "https://poe.ninja"
    api.client = _FakeClient()
    api.rate_limiter = _FakeRateLimiter()
    api.cache_manager = None
    return api


# ---------------------------------------------------------------------------
# Retirement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_character_is_retired():
    """The snapshot-backed get_character always returns None and makes NO
    network calls — the dead chain is gone, not just short-circuited."""
    api = _api()
    result = await api.get_character("Acct", "Char", "Runes of Aldur")
    assert result is None
    assert api.client.requested == []


def test_dead_chain_methods_deleted():
    """The snapshot/HTML-scrape chain must not survive as dead code."""
    for gone in (
        "_fetch_character_from_api",
        "_get_index_state",
        "_scrape_character_page",
        "_parse_character_html",
        "_normalize_api_character_data",
    ):
        assert not hasattr(PoeNinjaAPI, gone), f"{gone} should be deleted"


# ---------------------------------------------------------------------------
# Enumeration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_account_characters():
    api = _api()
    chars = await api.list_account_characters("Tomawar40-2671")
    assert chars == CHAR_LIST
    # SSE first, then the versioned list URL
    assert "/poe2/api/events/characters/Tomawar40-2671" in api.client.requested[0]
    assert "/poe2/api/profile/characters/Tomawar40-2671/4197557768" in api.client.requested[1]


@pytest.mark.asyncio
async def test_list_returns_none_on_sse_failure():
    api = _api()
    api.client.sse_status = 404
    assert await api.list_account_characters("PrivateAcct") is None


@pytest.mark.asyncio
async def test_list_returns_none_on_unexpected_shape():
    api = _api()
    api.client.list_payload = {"error": "not a list"}
    assert await api.list_account_characters("Acct") is None


@pytest.mark.asyncio
async def test_resolve_character_league_case_insensitive():
    api = _api()
    assert await api.resolve_character_league("Acct", "tomawarthefifth") == "vaal"
    assert await api.resolve_character_league("Acct", "TomawarTheSeventh") == "runesofaldur"


@pytest.mark.asyncio
async def test_resolve_unknown_character_returns_none():
    api = _api()
    assert await api.resolve_character_league("Acct", "NoSuchChar") is None


# ---------------------------------------------------------------------------
# PoB export via profile flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pob_import_via_profile_flow():
    """League auto-resolved from enumeration, export read from charModel."""
    api = _api()
    code = await api.get_pob_import("Tomawar40-2671", "TomawarTheSeventh")
    assert code == "eNrFAKEEXPORT"
    # The resolved slug must appear in the char-level SSE + model URLs
    char_urls = [u for u in api.client.requested if "runesofaldur" in u]
    assert any("/poe2/api/events/character/" in u for u in char_urls)
    assert any("/model/" in u for u in char_urls)


@pytest.mark.asyncio
async def test_get_pob_import_no_export_in_model():
    api = _api()
    api.client.model_payload = {"type": "full", "charModel": {"name": "X"}}
    assert await api.get_pob_import("Acct", "TomawarTheSeventh") is None


@pytest.mark.asyncio
async def test_get_pob_import_unknown_character():
    api = _api()
    assert await api.get_pob_import("Acct", "NoSuchChar") is None

"""
poe.ninja SPA detection (Issue #61).

Patch 0.5 (2026-05-29) migrated poe.ninja's builds/character pages from
SvelteKit (with embedded `window.__NUXT__` / `window.__data` JSON) to an
Astro-rendered client-side SPA. The new HTML responses are 200 OK but
contain no embedded build data — all content loads via runtime XHR.

This module isolates the detection logic so:
  1. The scraper in poe_ninja_api.py can distinguish "SPA shell, no data"
     from "real data, parse failed" and surface that distinction.
  2. Unit tests can exercise the detection without pulling in the full
     poe_ninja_api module (which loads BeautifulSoup, httpx, etc.).
  3. When/if poe.ninja's new build-data endpoint shape is discovered,
     this module is the single place to update.

Lives outside the MCP heavy-import graph (no SQLAlchemy / no mcp_server)
per the light-module pattern (PR #123 / #124 / #125).
"""

from __future__ import annotations

from typing import Optional

# Markers that historically indicated embedded build data (pre-0.5 poe.ninja).
LEGACY_DATA_MARKERS = (
    "window.__NUXT__",
    "window.__data",
)

# Markers that indicate the Astro SPA framework — present in any post-0.5
# poe.ninja HTML response. Detection of an Astro shell with NO legacy
# markers is the signal that the build/character data isn't embedded.
ASTRO_MARKERS = (
    "/_astro/",  # Astro chunks served from assets.poe.ninja/_astro/
    "data-astro-",  # Astro hydration attrs
    "<astro-island",  # Astro Islands web component
    "astro:page",  # Astro client-side event names
)


def is_astro_spa_shell(html: str) -> bool:
    """Return True if the response is a post-0.5 Astro SPA shell with no
    embedded build data, False otherwise.

    Strict definition:
      - Contains at least one Astro marker, AND
      - Contains zero legacy data markers (no __NUXT__, no __data)

    A response that has Astro markers BUT also has embedded data (e.g. a
    future migration where the data is re-embedded) returns False so the
    parser keeps trying. Conservative on purpose: we don't want to misclassify
    a real data response and skip parsing it.
    """
    if not html:
        return False
    has_astro = any(m in html for m in ASTRO_MARKERS)
    if not has_astro:
        return False
    has_legacy_data = any(m in html for m in LEGACY_DATA_MARKERS)
    return not has_legacy_data


def has_embedded_build_data(html: str) -> bool:
    """Inverse-of-sorts: True when the HTML carries one of the pre-0.5
    embedded-data markers, regardless of Astro presence.

    Useful for "this looks like it should parse" decisions in the
    multi-tier scraper fallback.
    """
    if not html:
        return False
    return any(m in html for m in LEGACY_DATA_MARKERS)


def spa_migration_notice(
    account: Optional[str] = None,
    character: Optional[str] = None,
    league: Optional[str] = None,
    issue_number: int = 61,
) -> str:
    """Standardized human-facing notice for the SPA-blocked failure case.

    Used by handlers and scrapers that detect they cannot fetch via the
    legacy poe.ninja paths. All-ASCII output (consistent with the
    provenance banner contract in PR #122).
    """
    lines = [
        "poe.ninja SPA migration (Patch 0.5) - data path not available",
    ]
    if account or character or league:
        ident_parts = []
        if character:
            ident_parts.append(f"character={character}")
        if account:
            ident_parts.append(f"account={account}")
        if league:
            ident_parts.append(f"league={league}")
        lines.append("Target: " + ", ".join(ident_parts))
    lines.append("")
    lines.append(
        "poe.ninja migrated their builds/character pages to a client-side "
        "Astro SPA at/around Patch 0.5 (2026-05-29). The HTML response we "
        "got back is the empty SPA shell - no embedded build data. The "
        "endpoints this tool used pre-0.5 either return 404 or this shell."
    )
    lines.append("")
    lines.append(
        f"Tracked at https://github.com/HivemindOverlord/poe2-mcp/issues/{issue_number}. "
        "Builds-list/ladder enumeration has no MCP-side fix until poe.ninja's "
        "new runtime XHR endpoint shape is reverse-engineered. For "
        "SINGLE-character fetch, the no-auth profile API works "
        "(/poe2/api/events/character/... -> /poe2/api/profile/characters/"
        ".../model/{version}) - analyze_character uses it automatically. "
        "The old snapshot API (/poe2/api/builds/{version}/character) is dead "
        "and was retired in #133; do not re-chase it."
    )
    return "\n".join(lines)

"""
Tests for the SPA-shell detector (Issue #61).

Light-module pattern: src/api/poe_ninja_spa_detect.py has no heavy imports,
so these tests run instantly without pulling httpx / BeautifulSoup / etc.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.api.poe_ninja_spa_detect import (  # noqa: E402
    has_embedded_build_data,
    is_astro_spa_shell,
    spa_migration_notice,
)

# ---------------------------------------------------------------------------
# is_astro_spa_shell()
# ---------------------------------------------------------------------------


def test_astro_spa_shell_detects_typical_post_0_5_response():
    """Real-shape sample: Astro markers present, no legacy data markers."""
    html = """
    <!doctype html>
    <html lang="en">
      <head>
        <title>poe.ninja</title>
        <script type="module" src="https://assets.poe.ninja/_astro/main.CqfquTQY.mjs"></script>
      </head>
      <body>
        <astro-island data-astro-component-url="..."></astro-island>
        <div data-astro-cid-xyz>content loads via xhr</div>
      </body>
    </html>
    """
    assert is_astro_spa_shell(html) is True


def test_astro_spa_shell_false_on_legacy_nuxt_data():
    """Pre-0.5 SvelteKit response with embedded __NUXT__ must NOT match."""
    html = """
    <!doctype html>
    <script>window.__NUXT__={data:[{character:{name:"Test"}}]};</script>
    <body>real data</body>
    """
    assert is_astro_spa_shell(html) is False


def test_astro_spa_shell_false_when_astro_present_but_data_also_present():
    """Hybrid response: Astro framework loaded but data is embedded.
    Be conservative - if data exists, attempt parsing. The function
    returns False so the parser keeps trying."""
    html = """
    <!doctype html>
    <script type="module" src="https://assets.poe.ninja/_astro/x.mjs"></script>
    <script>window.__data={character:{name:"Hybrid"}};</script>
    """
    assert is_astro_spa_shell(html) is False


def test_astro_spa_shell_false_on_empty_html():
    assert is_astro_spa_shell("") is False


def test_astro_spa_shell_false_on_arbitrary_html():
    """Random HTML with no Astro markers - not the SPA failure mode."""
    html = "<html><body>404 Not Found</body></html>"
    assert is_astro_spa_shell(html) is False


def test_astro_spa_shell_detects_via_data_astro_attribute_only():
    """Real Astro pages have data-astro-* attributes even without /_astro/ refs."""
    html = "<html><body><div data-astro-cid-abc>x</div></body></html>"
    assert is_astro_spa_shell(html) is True


def test_astro_spa_shell_detects_via_astro_island_tag_only():
    html = '<html><body><astro-island uid="abc"></astro-island></body></html>'
    assert is_astro_spa_shell(html) is True


# ---------------------------------------------------------------------------
# has_embedded_build_data()
# ---------------------------------------------------------------------------


def test_has_embedded_build_data_true_on_nuxt():
    assert has_embedded_build_data("<script>window.__NUXT__={x:1};</script>")


def test_has_embedded_build_data_true_on_data_var():
    assert has_embedded_build_data("<script>window.__data={x:1};</script>")


def test_has_embedded_build_data_false_on_astro_shell():
    """The post-0.5 SPA shell carries neither legacy marker."""
    html = "<div data-astro-cid-x><astro-island/></div>"
    assert has_embedded_build_data(html) is False


def test_has_embedded_build_data_false_on_empty():
    assert has_embedded_build_data("") is False


# ---------------------------------------------------------------------------
# spa_migration_notice()
# ---------------------------------------------------------------------------


def test_notice_mentions_issue_number():
    out = spa_migration_notice()
    assert "issues/61" in out


def test_notice_includes_target_when_supplied():
    out = spa_migration_notice(account="acc#1234", character="MyChar", league="Runes of Aldur")
    assert "MyChar" in out
    assert "acc#1234" in out
    assert "Runes of Aldur" in out


def test_notice_no_target_section_when_all_none():
    out = spa_migration_notice()
    assert "Target:" not in out


def test_notice_is_ascii_safe():
    """Consistent with the provenance banner ASCII-only contract (PR #122)."""
    out = spa_migration_notice(account="acc", character="char", league="Standard")
    out.encode("ascii")  # raises if non-ASCII


def test_notice_explains_what_still_works():
    """The user should know analyze_character / per-character API may still work."""
    out = spa_migration_notice()
    assert "per-character JSON API" in out or "analyze_character" in out

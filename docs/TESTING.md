# Testing Guide

How to write tests for poe2-mcp without making the mistakes we've already made.

For broader contributor setup, see `docs/DEVELOPMENT.md`. This file is specifically about the test discipline that lives between "your code compiles" and "your code actually works the way users will invoke it."

---

## The one rule that catches the most bugs

**Any in-process handler test MUST `await mcp.initialize()` before calling a handler.**

Skipping it is the bug that produced "Gap H" and "Gap G" — both retracted as false-alarm production bugs in PR #106 and PR #106's follow-up comment. The handlers reported "Passive tree resolver not initialized" / "int+str TypeError" not because they were broken, but because my smoke test only ran `PoE2BuildOptimizerMCP()` (the constructor) and never the async `initialize()` method that actually wires up the database, cache, resolvers, mechanics KB, and downstream components.

In production (Claude Desktop / `poe2-mcp` console script / `python launch.py`), the stdio server calls `await initialize()` after construction. A test that skips it tests a code path no real user ever hits.

### The pattern (canonical template)

See `tests/test_explain_mechanic_provenance.py` (PR #109) for the established template. The shape:

```python
import pytest
import pytest_asyncio
from src.mcp_server import PoE2BuildOptimizerMCP


@pytest_asyncio.fixture(scope="module")
async def mcp():
    """Initialized MCP server — full async init done once per module."""
    instance = PoE2BuildOptimizerMCP()
    await instance.initialize()                       # <-- THIS LINE
    return instance


@pytest.mark.asyncio
async def test_some_handler_behavior(mcp):
    result = await mcp._handle_some_tool({"arg": "value"})
    assert "expected text" in result[0].text
```

**Module-scoped fixture is intentional** — `initialize()` takes ~5 seconds (loads ~16k mods, ~10k passive tree nodes, ~600 support gems, etc.). Sharing across the whole module's tests keeps the test file fast.

### Existing handler test files following this template

- `tests/test_explain_mechanic_provenance.py` — 8 tests, 6.34s, locks PR #101's two-tier behavior
- `tests/test_inspect_support_gem_wildfire.py` — 5 tests, 6.20s, locks PR #107's Tier-2 fallback

When you write a new handler test, copy the fixture from one of those files.

---

## When to use other test patterns

### Pure-function tests (no MCP)

For modules that don't need the full server — pure calculators, parsers, dataclasses, data accessors — just import the function and test it directly. No fixture needed.

Examples:
- `tests/test_mods_spec.py` — pure binary-format parser
- `tests/test_defense_calculator.py` — pure math
- `tests/test_game_data.py` — JSON loaders

These run in milliseconds. Use them whenever you can — they're the fastest test type and don't need pytest-asyncio.

### Dataset shape tests (no MCP, no fixtures)

For locking `data/game/*` JSON files — record counts, schema, manifest drift between metadata.json and the data file. See `tests/test_skill_gems_dataset.py`, `tests/test_stat_descriptions.py`, `tests/test_game_data_helpers.py`.

These catch the kind of bug where a re-extraction silently drops records or changes a stat_id format.

### Feature-detect skip (when stacking on an unmerged PR)

If your test depends on code that's in another open PR, add a feature-detect `pytest.mark.skipif`. The test should pass on main today (skipped) and activate automatically once the dependency PR merges.

Pattern: probe a source-file string marker the dependency PR introduces. Example from `tests/test_inspect_support_gem_wildfire.py`:

```python
_MCP_SOURCE = (PROJECT_ROOT / "src" / "mcp_server.py").read_text(encoding="utf-8")
PR107_LANDED = "Tier-2 fallback record from" in _MCP_SOURCE
needs_pr107 = pytest.mark.skipif(
    not PR107_LANDED,
    reason="src/mcp_server.py lacks PR #107 Tier-2 fallback wiring (not yet merged)",
)

@needs_pr107
@pytest.mark.asyncio
async def test_thing_that_requires_pr107(mcp):
    ...
```

This is preferred over branching from the dependency PR's branch — keeps PRs reviewable in isolation and avoids merge-conflict bookkeeping if the dependency PR gets revisions.

`tests/test_stat_descriptions.py` uses the same pattern for PR #99 helpers.

---

## When something is "broken" in a smoke test

Before opening a fix PR, **always re-test with `await mcp.initialize()`**. If you find the same symptom in a properly-initialized server, you have a real bug. If the symptom vanishes once you initialize properly, you had a methodology error.

We've already burned one fire of work on a non-bug because of this. Don't do it again.

The retraction details are preserved in `tests/mcp_accuracy_evaluation_2026-05-30.md` (search for "Retraction") if you need the longer story.

---

## Test naming + organization

- `tests/test_<module>.py` for pure-function tests
- `tests/test_<feature>_<dataset_or_handler>.py` for integration tests
- One module-scoped fixture per file when the file tests one MCP handler family
- Skip reasons should name the dependency PR explicitly so future contributors know what's blocked on what

---

## CI

`pytest tests/` runs all tests. Integration tests (anything with an MCP fixture) add ~5s per file for the init cost; pure-function tests run in milliseconds. Full suite is currently ~10s wall time when both PR #109 and PR #110 are merged.

If you add a test file that fails on main but passes on a feature branch, add the feature-detect skip pattern above so CI stays green.

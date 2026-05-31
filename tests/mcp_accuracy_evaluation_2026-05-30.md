# MCP Accuracy Re-Evaluation — Post Patch 0.5

**Evaluation Date:** 2026-05-30
**Patch context:** 0.5 "Return of the Ancients" + all data/game/ fresh extracts merged through PR #70
**Methodology:** For each question, answer WITHOUT MCP (model knowledge baseline) → answer WITH MCP (tool calls) → compare → log gaps.

Companion document: `mcp_accuracy_evaluation.md` (Jan 2026 / pre-0.5 baseline).

Character context: TomawarTheFifth (Level 91 Shaman) per `mcp_tool_test_questions.md`.

---

## Phase 1: Representative subset (5 questions)

Picked to span tool surfaces: passive (Q07), gem (Q11), support compatibility (Q14), mod search (Q19), knowledge base (Q26 — was worst-scored pre-0.5).

---

### Q07: `inspect_keystone` — "What does Resolute Technique do? Would it help my Shred build?"

#### Without MCP (model baseline)
- Trade: guaranteed hit (no evade) ↔ no critical strikes.
- For Shred (Druid Shapeshift): helps a non-crit / bleed-focused variant; hurts a crit variant.
- Confidence on trade direction: HIGH. Confidence on exact wording: MEDIUM.

#### With MCP
```
# Resolute Technique
**Type:** Keystone   **Node ID:** 44017
## Stats
- Accuracy Rating is Doubled
- Never deal Critical Hits
**Connected to 1 nodes**
```

#### Comparison
- **MCP correct on stat text.** Slightly different from my hedged recall ("Hits cannot be Evaded" vs "Accuracy Rating is Doubled" — both have the same end effect; MCP wording is the canonical PoE2 phrasing).
- **MCP MISSING the build-advice layer.** It gave the raw stat but not "would it help my Shred build?" — no synthesis. A user asking the question gets data, not an answer.
- **Verdict:** MCP > baseline on facts; baseline > MCP on actionable advice. The MCP should arguably defer build-advice synthesis to the calling LLM (the project's stated "MCP = data layer, Claude = intelligence layer" philosophy), so this isn't necessarily wrong — but the LLM needs to know to do the synthesis layer.

---

### Q11: `inspect_spell_gem` — "What are the exact stats and tags for Shred?"

#### Without MCP (model baseline)
- Tags I guessed: Melee, Attack, Physical, Shapeshift, Werewolf, AoE.
- Cast time: ~1.0s.
- No precise base damage / per-level values.

#### With MCP
```
# Shred
**ID**: WolfShredPlayer
**Skill Types**: Attack, Melee, MeleeSingleTarget, Shapeshift, Wolf, PerformsFinalStrike
**Cast Time**: 1.0s
**Per-Level**: L1 baseMultiplier=0.40, L10=0.77, L20=1.25
**Stat Sets**: Normal Strikes / Fast Strikes (+35% attack speed) / Final Strike (-55% attack speed, +6 melee range)
**Quality**: +0.5% attack speed per 1% quality
**Data Source**: pob_complete_skills.json (Path of Building, 2025-12-13)
```

#### Comparison
- **MCP much richer than baseline.** Per-level base multipliers, three distinct stat sets (Normal/Fast/Final Strike with different speed modifiers), quality bonus formula.
- **One correction to my baseline:** my guess of "AoE" tag was wrong — actual is `MeleeSingleTarget`. Shred is single-target, not AoE.
- **Important note in the data source line:** `pob_complete_skills.json (2025-12-13)` — this is **PRE-0.5 data**. The skill data is stale. The cast time, tags, and base multipliers may have changed in 0.5. This is documented as `skill_gems` still pending re-extraction in `data/game/version.json` (blocked on PoB2 community shipping 0.5 tree.json upstream).
- **Verdict:** MCP > baseline on data depth; **both stale for 0.5**; MCP is honest about the data source date.

---

### Q14: `validate_support_combination` — "Can I use Rage and Brutality together on my Shred setup?"

#### Without MCP (model baseline)
- Mechanically compatible (no hard exclusion family).
- **Strategically wrong** for a Shred build leveraging cold (Lunar/Ice Fragment synergy): Brutality blocks all non-physical damage, killing the cold scaling.
- Recommended answer: "yes mechanically, but probably no for this build."

#### With MCP
```
Valid combination: Rage, Brutality
Reason: All supports are compatible
```

#### Comparison
- **MCP technically correct, contextually shallow.** It checks the hardcoded incompatibility list (`HARDCODED_INCOMPATIBILITIES` in `gem_synergy_calculator.py`) and reports YES. That's accurate for "are they allowed to be in the same setup."
- **MCP MISSING:** the synergy implication (Brutality + non-physical-scaling skills = build trap). A user asking the question would receive the wrong impression that this is a fine setup.
- **Possible fix:** `validate_support_combination` could surface "more"-multiplier interactions, damage-type restrictions, and skill-tag conflicts (e.g. Brutality + skill that benefits from elemental scaling). That's a small handler-layer enrichment — read each support's effect tags and warn when they conflict with the SKILL's natural scaling.
- **Verdict:** MCP < baseline on usefulness; gap is well-defined and fixable.

---

### Q19: `search_mods_by_stat` — "Find all mods that grant life regeneration"

#### Without MCP (model baseline)
- Knew the mod categories existed (implicit on certain bases, suffix "of Recovery"-style on body armour/belts/helmets/jewels).
- Couldn't name exact mod IDs or tier magnitudes.

#### With MCP
```
# Mods Search: 'life regeneration'
**Found:** 0 mods
*No mods found matching your search.*
```

#### Comparison
- **MCP fully broken on this query.** Returns 0 mods. We have **16,788 mods** in `data/game/mods/mods.json` with stat text — life regen mods definitely exist (Vitality, Recovery, Health Regeneration families).
- This is **Gap 9 from the Jan 2026 eval** — still not fixed. The search appears to be looking at the OLD data source, OR the search algorithm doesn't tokenize "life regeneration" → "life_regeneration" / "base_life_regeneration_rate_per_second" / etc. correctly.
- **Verdict:** MCP fails this question. **Concrete gap, P0 priority** for the next sweep.

---

### Q26: `explain_mechanic` — "How does Rage work? I'm using Rage support on Shred"

#### Without MCP (model baseline)
Cross-referenced from Jan eval external sources:
- 1% **MORE** Attack Damage per Rage (multiplicative).
- Max 30 (down from PoE1's 50).
- Decay 5/sec after 4-sec grace.

#### With MCP
*(Full answer captured in the tool output — abbreviated here)*
- ✅ 1% **MORE** Attack Damage per Rage (explicitly marked "multiplicative, not additive!")
- ✅ Max 30 (with explicit "NOT 50 like PoE1!")
- ✅ Decay 5/sec after 4 sec grace
- ✅ Attack-only (doesn't affect spells, doesn't affect ailment damage)
- ✅ Berserk interaction explained
- ✅ Blood of the Warrior flask / Death Articulated gloves noted
- ✅ Common questions section addressing 7 typical follow-ups
- ✅ Changes-from-PoE1 section explicitly enumerates the differences

#### Comparison
- **MAJOR WIN.** This was the **worst-scored item** in the Jan 2026 eval (3 critical errors flagged). Now it's **completely correct** with all the citations baked in.
- Someone fixed `poe2_mechanics.py` since January per the Jan eval's recommendations. The fix is excellent — explicit warnings about common confusion points (more vs increased, max from PoE1).
- **Verdict:** MCP >> baseline. This is a model of what a good `explain_mechanic` entry looks like. Use this as the template for the Runic Ward entry I added in PR #64 (which is preliminary).

---

## Phase 3: Gap inventory + recommended fixes

### NEW gaps found this sample

| # | Gap | Severity | Surface | Fix path |
|---|-----|----------|---------|----------|
| **A** | `inspect_keystone` requires `keystone_name` not `name` | LOW (AI-friendliness) | Schema | Add `name` alias OR document the canonical param more visibly |
| **B** | `inspect_spell_gem` requires `spell_name` not `gem_name` | LOW (AI-friendliness) | Schema | Same — alias the field, or use the most-natural name |
| **C** | `validate_support_combination` requires `support_gems` not `support_gem_names` | LOW (AI-friendliness) | Schema | Same |
| **D** | `validate_support_combination` doesn't surface damage-type conflicts (e.g. Brutality on cold-scaling skill) | MEDIUM | Handler logic | Cross-reference support gem effect tags against the SKILL's damage scaling; warn on mismatch |
| **E** | `inspect_spell_gem` data source is `pob_complete_skills.json (2025-12-13)` — pre-0.5 stale | MEDIUM | Data | Port `skill_gems` to `data/game/skill_gems/` once PoB2 ships 0.5 tree.json (still blocked) |
| **F** | `search_mods_by_stat` returns 0 results for "life regeneration" despite 16,788 mods in DB | **HIGH** | Handler logic + indexing | Wire to `data/game/mods/mods.json`; implement tokenized substring search against display_name + stat_id (after stat_key→stat_id cross-reference enrichment) |

### Gaps STILL OPEN from Jan 2026 eval (sample subset)

| Old gap | Today's status |
|---|---|
| #1 Rage mechanics wrong | ✅ **FIXED** (Q26 verifies) |
| #9 Mod stat text search broken | ❌ **Still broken** (Q19 verifies — Gap F above) |

### Gaps RESOLVED since Jan 2026 (worth celebrating)

- Q26 (Rage): full-fidelity, all three Jan-flagged errors corrected, plus added depth.

### A.I.-friendliness observations (operator's stated goal)

The 3 parameter-name mismatches (A/B/C) are exactly the kind of friction that makes an LLM caller fail-then-retry rather than succeed-first-shot. Standardizing on one of two conventions would fix this:
- **Option 1: bare nouns** — `name`, `id`, `query`. Shortest, most LLM-intuitive.
- **Option 2: typed nouns** — `keystone_name`, `spell_name`, `support_gem_names`. Most explicit, current convention but inconsistent (`name` for some tools, `keystone_name` for others).

Recommendation: **adopt bare-noun convention** with the current typed-noun names kept as aliases for back-compat. Single small PR to `mcp_server.py` tool-schema definitions.

---

## Phase 4: Recommended PRs from this sample

Capped at HivemindOverlord's review-load preference of ~3 simultaneous open PRs. Ordered by impact:

1. **Fix `search_mods_by_stat` (Gap F)** — wire to fresh `data/game/mods/`, add tokenized substring search across `display_name` + `stat_id` (requires also doing the stat_key → stat_id enrichment from backlog item #2). HIGH impact: unblocks a whole class of "find mods that…" questions.
2. **Tool-schema alias pass (Gaps A/B/C)** — add bare-noun aliases to the 3 mis-matched tools (and any others a wider sweep finds). LOW risk, immediate AI-friendliness win.
3. **`validate_support_combination` enrichment (Gap D)** — surface damage-type conflicts. MEDIUM impact, MEDIUM risk (might generate false positives if not carefully scoped — should warn-not-error).

**Skill_gems re-extraction (Gap E)** stays blocked on PoB2 upstream; not actionable until they ship 0.5 tree.json.

---

## Phase 5: Continuation

25 questions remain. Pattern is now established:
1. Answer WITHOUT MCP (baseline)
2. Answer WITH MCP (tool calls)
3. Compare → categorize as MCP-wins / baseline-wins / both-correct / both-wrong
4. Append to gap inventory
5. Triage fixes into PRs (cap 3 open)

Next batch suggestion: Q01 + Q02 (character analysis flow), Q05 + Q09 (passive tree depth — uses fresh 0.5 data), Q22 + Q23 (item mod validation flow), Q24 + Q25 (build constraints + formulas).

---

## Batch 2 (2026-05-31 cron fire 3) — Q05, Q09, Q26-confirm

Picked 2 passive-tree questions to exercise the fresh 0.5 data (data/game/passive_tree/, 9,605 nodes, shipped in PR #69). Plus an opportunistic confirm of Q26 (Rage) which was the eval's big win in batch 1.

### Q09: `inspect_passive_node` — `node_id=44017` (the Resolute Technique node we used in Q07)

#### Without MCP
- I'd guess "needs the integer ID poe.ninja uses" and not be able to look it up cold.
- I do know Resolute Technique's stats from Q07 batch 1: Accuracy×2, no crits.

#### With MCP
```
# Resolute Technique
**Type:** Keystone   **Node ID:** 44017   **Position:** (-7861, 2932)
## Stats
- Accuracy Rating is Doubled
- Never deal Critical Hits
## Connections
Connected to 1 adjacent nodes.
```

#### Comparison
- **Works cleanly.** MCP returns canonical stats + position + connection count. Position coords are a bonus over Q07's `inspect_keystone` output.
- **Confirms PR #69's `data/game/passive_tree/tree.json` is wired into this handler.** Node ID 44017 (string-keyed under `"44017"` in the JSON dict — I just verified) resolves to the keystone correctly.
- **Verdict:** MCP > baseline on data. Tool works as advertised.

---

### Q05: `analyze_passive_tree` — five sample node IDs `[44017, 6178, 1023, 5511, 28091]`

#### Without MCP
- For a list of integer node IDs, I'd have no way to resolve them without the data on hand.
- Could maybe guess Resolute Technique (44017) from earlier work but the others are unknown.

#### With MCP
```
# Passive Tree Analysis
## Summary
- Total Nodes Allocated: 5
- Starting Class: Unknown
- Build Connected: NO - Disconnected nodes detected!

## Keystones (1)
### Resolute Technique
## Notables (1)
### Power Shots
  - 15% reduced Attack Speed with Crossbows
  - 80% increased Critical Damage Bonus with Crossbows

## Nearest Unallocated Notables (5 listed)
### Efficient Loading (2 away)  ...

## Unresolved Nodes (3)
*These are likely ascendancy nodes not in the main passive tree database.*
Node IDs: [1023, 5511, 28091]
**Tip:** Use `get_ascendancy_info` tool to look up ascendancy node details.
```

#### Comparison
- **MCP works AND gives actionable downstream guidance.** Resolved 2 of 5 (Resolute Technique keystone, Power Shots notable — distinctly PoE2 0.5 content, crossbow-specific), correctly identified 3 as unresolved with the helpful tip pointing to `get_ascendancy_info`.
- **PR #69 data is live in this handler too.** Power Shots is a PoE2 0.5 notable; the fact that it resolves means the passive tree handler is reading the fresh data.
- **Improvement opportunity:** the "Starting Class: Unknown" line is uninformative. Could improve heuristic — given the allocated nodes include crossbow-themed Power Shots, "likely Mercenary" would be a useful hint. Low priority; saving for backlog.
- **Verdict:** MCP > baseline. Tool works AND degrades gracefully when nodes are unresolvable (vs the silent-failure of the bad search_mods_by_stat we fixed in PR #73).

---

### NEW BUG FOUND: `list_all_keystones` runtime error

Probing for keystone IDs to feed into Q05, called `list_all_keystones(limit=5)`. Got:

```
Error: unsupported operand type(s) for +: 'int' and 'str'
```

Complete tool failure — Python TypeError, likely in the response-formatting code mixing an int and a string with `+`. Definitely a real bug.

**Gap G** (NEW): `list_all_keystones` runtime error.
- **Severity:** HIGH — tool is totally broken, returns no data
- **Surface:** handler in `mcp_server.py`
- **Fix path:** trace the TypeError, likely `response += some_int` somewhere — fix to use string formatting
- **Rule 12 status:** mcp_server.py is open in PR #76 — this fix DEFERS until #76 merges, then ships as a follow-up. Logging the gap here so it isn't lost.

---

### Q26 confirm: `explain_mechanic(mechanic_name="rage")` — still correct

Re-ran the mechanic call to verify the Rage fix from batch 1 hasn't regressed. Output unchanged: 30 max, 5/sec decay, "MORE" not "increased", attack-only. ✅ Stable.

---

## Gap inventory (batch 1 + batch 2)

| # | Gap | Severity | Surface | Status |
|---|-----|----------|---------|--------|
| A | `inspect_keystone` requires `keystone_name` not `name` | LOW | Schema | ✅ FIXED in PR #73 |
| B | `inspect_spell_gem` requires `spell_name` not `gem_name` | LOW | Schema | ✅ FIXED in PR #73 |
| C | `validate_support_combination` requires `support_gems` not `support_gem_names` | LOW | Schema | ✅ FIXED in PR #73 |
| D | `validate_support_combination` doesn't surface damage-type conflicts | MED | Handler | OPEN (backlog item 6) |
| E | `inspect_spell_gem` data source pre-0.5 stale | MED | Data | BLOCKED on PoB2 0.5 |
| F | `search_mods_by_stat` returns 0 for "life regeneration" | HIGH | Handler | ✅ FIXED in PR #73 |
| **G** | **`list_all_keystones` runtime error (int + str)** | **HIGH** | **Handler** | **NEW — deferred until PR #76 lands** |

---

---

## Batch 3 (2026-05-31, fire 23 @ 15-min cadence)

### Q06: `list_all_keystones` — "What keystones benefit a physical attack Shaman with minions?"

Called `list_all_keystones(limit=10)`. Got:

```
Error: Passive tree resolver not initialized. PSG database may be missing.
```

This is a DIFFERENT error from Gap G's int+str TypeError. The handler is failing earlier, at resolver-initialization stage. Returns no data whatsoever — tool is completely dead, not even returning a TypeError from formatter code.

### Q08: `list_all_notables` — "Show me notables that grant increased physical damage or life"

Same call pattern, same error:

```
Error: Passive tree resolver not initialized. PSG database may be missing.
```

`grep -n "Passive tree resolver not initialized" src/mcp_server.py` shows the string at **5 locations** (lines 4051, 4233, 4314, 4372, 4427), suggesting at least 5 passive-tree-adjacent handlers share this dependency. So this single bug likely breaks: `list_all_keystones`, `list_all_notables`, `inspect_keystone`, `inspect_passive_node`, plus one more.

Gap G (int+str TypeError) was never actually validated — the resolver fails earlier, so the int+str code path was never reached in batch 2. **Gap G may not exist** — or may exist but is masked by Gap H. Reclassify Gap G as "Gap G/H combined: passive-tree handlers fail at resolver init."

### NEW BUG FOUND: Passive-tree resolver init failure

**Gap H** (NEW, supersedes / contains Gap G): Multiple passive-tree handlers (`list_all_keystones`, `list_all_notables`, and ≥3 others) fail with "Passive tree resolver not initialized. PSG database may be missing."

- **Severity:** CRITICAL — entire passive-tree query surface unusable
- **Surface:** handler/resolver init in `src/mcp_server.py` + likely `src/parsers/passive_tree_resolver.py`
- **Root cause hypothesis:** the resolver expects `data/extracted/metadata/passiveskillgraph.psg` (raw .psg blob, gitignored per data-extraction policy) but we now ship the structured `data/game/passive_tree/tree.json` instead. The resolver hasn't been rewired to the new data path. Same pattern as the `inspect_spell_gem` / `list_all_spells` rewiring PR #94 did for skill_gems — needs the equivalent for passive tree.
- **Fix path:** rewire the resolver init to load from `data/game/passive_tree/tree.json` (already on main since PR #69). Likely 1-handler-helper-file change. Touches `src/mcp_server.py` so currently blocked by Rule 12 conflict with PR #94 (handlers branch). Ship after #94 lands.
- **User impact:** any AI client trying to answer "show me keystones for X build" or "what notables grant Y" gets back a meaningless error.

---

## Gap inventory (batch 1 + batch 2 + batch 3)

| # | Gap | Severity | Surface | Status |
|---|-----|----------|---------|--------|
| A | `inspect_keystone` requires `keystone_name` not `name` | LOW | Schema | ✅ FIXED in PR #73 |
| B | `inspect_spell_gem` requires `spell_name` not `gem_name` | LOW | Schema | ✅ FIXED in PR #73 |
| C | `validate_support_combination` requires `support_gems` not `support_gem_names` | LOW | Schema | ✅ FIXED in PR #73 |
| D | `validate_support_combination` doesn't surface damage-type conflicts | MED | Handler | OPEN (backlog item 6) |
| E | `inspect_spell_gem` data source pre-0.5 stale | MED | Data | ✅ FIXED (PR #91 ships skill_gems v1, PR #94 wires handlers) |
| F | `search_mods_by_stat` returns 0 for "life regeneration" | HIGH | Handler | ✅ FIXED in PR #73 |
| G | `list_all_keystones` runtime error (int + str) | HIGH | Handler | RECLASSIFIED — masked by Gap H (which itself was a test artifact); status unknown until re-tested with proper init |
| H | Passive-tree resolver init failure | ~~CRITICAL~~ → **NOT A BUG** | ~~Resolver init~~ → **Test methodology error** | **RETRACTED 2026-05-31 fire 28** — see retraction note below |

---

## Retraction — Gap H was a test-methodology error, not a production bug (fire 28, 2026-05-31)

**Re-tested after PR #101 merged.** Verified the resolver loads cleanly in production:

```
$ python -c "import asyncio, sys; sys.path.insert(0,'.')
from src.mcp_server import PoE2BuildOptimizerMCP
async def go():
    mcp = PoE2BuildOptimizerMCP()
    await mcp.initialize()                # <-- the missing piece in batch-3 smoke test
asyncio.run(go())"

[...]
INFO - Loaded 4975 passive nodes
INFO - Passive tree resolver initialized (4975 nodes)
INFO - PoE2 Build Optimizer MCP Server initialized successfully
```

**Root cause of the false alarm:** my batch-3 smoke test invoked `mcp = PoE2BuildOptimizerMCP()` and called handlers directly — but the resolver lives in the **async `initialize()` method**, not `__init__`. Without `await mcp.initialize()`, the resolver attribute stays `None`, every passive-tree handler short-circuits to "resolver not initialized", and I incorrectly concluded the production code was broken.

In production (Claude Desktop / `poe2-mcp` console script / `python launch.py`), the stdio server calls `await initialize()` after construction, so the resolver is ready before any handler runs.

**Lesson — eval-batch smoke test methodology rule going forward:**
> Any handler exercised via in-process smoke test MUST be preceded by `await mcp.initialize()`. Skipping it tests the wrong code path and produces false "broken" claims. This affects roughly anything that depends on `self.db_manager`, `self.cache_manager`, `self.rate_limiter`, `self.passive_tree_resolver`, `self.mechanics_kb`, `self.pob_*`, or any AI component — i.e. most non-trivial handlers.

**Real status of Gap G + H stat:** unknown. The int+str TypeError (Gap G) was reported pre-batch-3; whether it's real or also a test-environment artifact won't be known until someone re-runs against a properly-initialized server. Re-test belongs in batch 4 with the methodology fix above applied.

## Continuation queue (20 questions remaining)

Batch 4 candidates (disjoint files / quick wins given the new gap landscape):
- Q12 `list_all_supports` + Q13 `inspect_support_gem` — tests support data (different data source than passive tree, so Gap H doesn't affect these)
- Q22 `validate_item_mods` + Q23 `get_available_mods` — tests mod-system validation with fresh 0.5 mods
- Q24 `validate_build_constraints` + Q27 `get_formula` — pure-computation tools, no data-source risk
- Q10 `list_all_spells` — now Tier-1 via skill_gems per PR #94, would verify the 83-spell count holds end-to-end
- Q24 `validate_build_constraints` + Q25 `get_formula` (tests calculator stack — was Gap 7 in Jan eval)

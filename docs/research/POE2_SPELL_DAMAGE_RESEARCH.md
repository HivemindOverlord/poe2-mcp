# Path of Exile 2 Spell Damage Calculation Research

**Date:** 2025-10-23
**Purpose:** Comprehensive research on PoE2 spell damage formulas for DPS calculator implementation
**Status:** Research Complete - Ready for Implementation

---

## Table of Contents

1. [General Spell Damage Formula](#general-spell-damage-formula)
2. [Order of Operations](#order-of-operations)
3. [Specific Spell Mechanics](#specific-spell-mechanics)
4. [Damage Modifiers](#damage-modifiers)
5. [Support Gem Interactions](#support-gem-interactions)
6. [Critical Strike System](#critical-strike-system)
7. [Resistance and Penetration](#resistance-and-penetration)
8. [Damage Conversion](#damage-conversion)
9. [Special Mechanics](#special-mechanics)
10. [Official Sources](#official-sources)

---

## 1. General Spell Damage Formula

### Core Formula

```
Final Damage = (Base Damage + Added Damage) × (1 + Sum of Increased/Decreased) × (Product of More/Less Multipliers) × Critical Multiplier × Resistance Multiplier
```

### Simplified Step-by-Step

1. **Base Damage**: Determined by spell gem level (not weapon damage)
2. **Added Damage**: Flat damage from gear/supports, multiplied by Damage Effectiveness
3. **Increased/Decreased**: All additive modifiers summed together
4. **More/Less**: Each multiplier applied multiplicatively
5. **Critical Strike**: Applied if crit roll succeeds
6. **Resistance**: Enemy resistance/penetration applied last

### Example Calculation

```
Base: 100 Cold Damage (from gem level 15)
Added: +50 Cold Damage (after damage effectiveness)
Increased: 300% increased spell damage
More: 40% more (Hourglass) + 20% more (support) = 1.4 × 1.2 = 1.68
Casts/sec: 2.0

Step 1: 100 + 50 = 150 base
Step 2: 150 × (1 + 3.0) = 150 × 4.0 = 600
Step 3: 600 × 1.68 = 1,008
Step 4: 1,008 × 2.0 casts/sec = 2,016 DPS
```

**Source:** Maxroll.gg PoE2 Damage Scaling Guide

---

## 2. Order of Operations

### Complete Damage Calculation Order

1. **Damage Conversion** (if applicable)
   - Skill-inherent conversion first
   - Gear/passive conversion second
   - Normalized to 100% if exceeded

2. **Base Damage Calculation**
   - For spells: Gem level determines base damage
   - For attacks: Weapon damage

3. **Added Damage Application**
   - Spells: `Added Damage × Damage Effectiveness + Base Damage`
   - Attacks: `(Base + Added Damage) × Damage Effectiveness`
   - **Key Difference**: Spells multiply ONLY added damage by effectiveness

4. **Damage Gain** (e.g., "Gain X% of Physical as Fire")
   - Calculated before scaling modifiers
   - Additive with other gain sources
   - Multiplicative with damage scaling

5. **Increased/Decreased Modifiers**
   - Formula: `(1 + Sum of All Increases - Sum of All Decreases)`
   - All sources stack additively (diminishing returns)
   - Applied as single multiplier

6. **More/Less Modifiers**
   - Each source multiplies separately
   - Formula: `Product of (1 + More1) × (1 + More2) × ...`
   - Example: 25% more × 25% more = 1.25 × 1.25 = 1.5625 (56.25% total increase)

7. **Critical Strike Calculation** (if hit crits)
   - Base: +100% critical damage bonus (200% total damage)
   - Formula: `(1 + Base Crit Bonus + Added Crit Bonus) × (1 + Increased Crit Damage) × Product of More Crit Multipliers`
   - PoE2 uses "Critical Damage Bonus" instead of PoE1's "Critical Strike Multiplier"

8. **Resistance/Penetration Application**
   - Exposure/Curses applied first (can go negative)
   - Penetration applied second (cannot go below 0% except with Leopold's Applause)
   - Formula: `Effective Resistance = min(Resistance, Max Resistance) - Penetration`

9. **Final Damage Mitigation**
   - Armour (for physical damage)
   - Evasion/Dodge (hit avoidance - separate from damage calc)

**Sources:**
- Maxroll.gg Damage Scaling
- Mobalytics.gg Order of Operations Guide
- PoE Wiki (poewiki.net)

---

## 3. Specific Spell Mechanics

### Lightning Spells

#### Arc (Chain Lightning)
- **Base Mechanic**: Chains between enemies
- **Chains**: 6-9 times at gem levels 5-20
- **Chain Range**: 3.5 metres
- **Damage Scaling**: **15% MORE damage per REMAINING chain**
  - Single target: Full chains remaining = maximum damage
  - This is a "more" multiplier, not "increased"
- **Special**: Secondary Arc created at each chain (cannot chain further)
- **Recent Changes**:
  - 50% more shock magnitude (Patch 0.3.0)
  - Quality bonus: +0-2 additional chains (changed from damage bonus)
  - Can consume Lightning Infusion to chain additional times
- **Tags**: Spell, Lightning, Chaining
- **Critical Strike Chance**: Varies by gem level
- **Source:** poe2db.tw, maxroll.gg, pathofexile2.wiki.fextralife.com

#### Spark (Projectile)
- **Base Damage**: (1-11) to (10-216) Lightning Damage
- **Projectiles**: Fires 4-9 projectiles (scales with gem level)
- **Duration**: 2 seconds base
- **Behavior**: Projectiles travel erratically along the ground
- **Hit Limitation**: Same projectile wave cannot hit same target more than once every 0.66 seconds
- **Cast Time**: 0.70 seconds
- **Critical Strike Chance**: 9.00%
- **Cold-Infused Version**:
  - Damage: (7-182) to (11-273) Cold + (1-11) to (10-216) Lightning
  - Projectiles: 12-16 in a circle
  - Cast Time: +0.5 seconds (1.2 total)
  - Critical Strike Chance: 11.00%
- **Tags**: Spell, Projectile, Lightning
- **Scaling**: Affected by Spell, Projectile, Lightning, and Elemental damage modifiers
- **Source:** poewiki.net, poe2db.tw

#### Lightning Conduit
- **Base Mechanic**: Cone AoE that deals significantly more damage to shocked enemies
- **Tier**: 13
- **Cooldown**: 8.00 seconds (6 seconds previously mentioned)
- **Charges**: 1 charge storage
- **Cast Time**: 1.00 second
- **Critical Strike Chance**: 10%
- **Mana Cost**: 19-195 (scales with level)
- **Damage**:
  - Gem level 13: 69-208 damage (previously 41-123)
  - Gem level 20: 189-568 damage (previously 99-297)
- **Key Change**: No longer consumes Shock from targets
- **Synergies**: Works with "Cast on Shock" support for automatic triggering
- **Tags**: Spell, Lightning, Area
- **Source:** pathofexile2.wiki.fextralife.com, poe2db.tw

#### Orb of Storms
- **Base Damage**: (1-14) to (8-260) Lightning Damage (gem level 1-20)
- **Trigger Mechanic**: Fires bolt every 4 seconds AND when you cast ANY spell near the orb
- **Radius**: 3.6 metres
- **Duration**: 12 seconds
- **Bolts**: Expires after firing 6 bolts
- **Chaining**: Chains 3-5 times (scales with quality)
- **Recent Changes**:
  - Now triggers from ANY spell in radius (previously only lightning spells)
  - Creates Lightning Infusion Remnant when expired or all bolts used
- **Tags**: Spell, Lightning, Area, Duration, Chaining
- **Source:** poewiki.net, poe2db.tw

### Cold Spells

#### Frostbolt
- **Base Mechanic**: Slow-moving piercing projectile
- **Special Interaction**: Ice Nova and Snap can be cast on Frostbolt projectiles
- **Wake Effect**: Leaves chilled ground behind it
- **Explosion Radius**: 3.2 metres (when detonated by Ice Nova/Snap)
- **Special Bonus**: 50% more damage with hits for blasts from unique enemies
- **Tags**: Spell, Projectile, Cold
- **Source:** poewiki.net, poe2wiki.net

#### Ice Nova
- **Base Mechanic**: Wave of ice in all directions
- **Radius**: 3.2 metres
- **Cast Time**: 1.00 second
- **Critical Strike Chance**: 12.00%
- **Special Effects**:
  - 100% more magnitude of chill
  - 100-157% more freeze buildup
  - Knocks back enemies
- **Frostbolt Synergy**: Can be cast targeting Frostbolt to originate from projectile
- **Endgame Transition**: Snakepit ring makes Frostbolts detonate on impact (superior to Ice Nova)
- **Tags**: Spell, Cold, Area
- **Source:** pathofexile2.wiki.fextralife.com, poewiki.net

#### Freezing Pulse
- **Base Mechanic**: Icy projectile that fades quickly
- **Damage Scaling**: Damage and freeze chance REDUCE as projectile travels
- **Behavior**: Projectile dissipates over distance
- **Freeze Chance**: Chance to freeze diminishes with distance
- **Tags**: Spell, Projectile, Cold
- **Source:** pathofexile.fandom.com, poedb.tw

#### Frost Bomb
- **Primary Use**: Applies Cold Exposure (resistance reduction)
- **Base Exposure**: 20% Elemental Exposure
- **Scaling**: Up to 50% Elemental Exposure based on number of pulses hitting target
- **Interaction**: Scouring Winds ascendancy node doubles Exposure effectiveness
- **Boss Rotation**: Cast first to apply exposure, then use main damage skills
- **Tags**: Spell, Cold, Area, Duration
- **Source:** mobalytics.gg build guides

### Fire Spells

#### Fireball
- **Base Mechanic**: Large ball of fire that explodes on impact
- **Explosion**: AoE damage on impact
- **Frost Wall Synergy**: Splits into multiple projectiles when hitting walls/obstacles
- **Flame Wall Synergy**: Projectiles passing through Flame Wall gain added fire damage
- **Tags**: Spell, Projectile, Fire
- **Source:** maxroll.gg, mobalytics.gg

#### Flame Wall
- **Tier**: 3
- **Base Mechanic**: Creates wall of fire in front of character
- **Direct Effect**: Ignites everything within area
- **Projectile Bonus**: Projectiles (yours and allies) passing through gain:
  - Added fire damage
  - Inflict Ignite on hit
- **Tags**: Spell, Fire, Area, Duration
- **Source:** sportskeeda.com spell list

#### Ember Fusillade
- **Tier**: 3
- **Base Mechanic**: Conjures blazing Ember hovering above you
- **Lightning Infusion Interaction**: Consumes Lightning to create chaining beam from each Ember
- **Tags**: Spell, Fire
- **Source:** sportskeeda.com spell list

#### Incinerate
- **Tier**: 5
- **Base Mechanic**: Channeling spell - torrent of fire from your hand
- **Scaling**: Flames grow stronger the longer you channel
- **Maximum Strength Effects**:
  - Applies stacking Fire Exposure
  - Creates Burning Ground
- **Ignite**: Ignites enemies in front of you
- **Tags**: Spell, Fire, Channeling, Area
- **Source:** sportskeeda.com spell list

---

## 4. Damage Modifiers

### Increased/Decreased Spell Damage

**Formula**: `(1 + Sum of All Increases - Sum of All Decreases)`

**Characteristics**:
- All sources stack additively (diminishing returns)
- Common sources:
  - Passive tree nodes
  - Equipment (% increased spell damage)
  - Skill tree clusters
  - Temporary buffs

**Example**:
```
20% increased + 30% increased + 50% increased = 100% increased
= (1 + 1.0) = 2.0x multiplier

NOT: 1.2 × 1.3 × 1.5 = 2.34x
```

**Source:** All PoE2 damage guides

---

### More/Less Spell Damage

**Formula**: `Product of (1 + More1) × (1 + More2) × ...`

**Characteristics**:
- Each source multiplies separately (exponential scaling)
- Much rarer than "increased" modifiers
- Primary sources:
  - Support gems (most common)
  - Ascendancy notables
  - Unique item modifiers
  - Skill gem modifiers

**Example**:
```
25% more × 25% more = 1.25 × 1.25 = 1.5625 (56.25% total)
40% more × 20% more = 1.40 × 1.20 = 1.68 (68% total)
```

**Importance**: More multipliers are the key to significant damage boosts. Support gems are valuable specifically because they provide "more" multipliers.

**Source:** Maxroll.gg, Mobalytics.gg

---

### Added Damage (Flat Fire/Cold/Lightning)

**Spell Application Formula**:
```
Total Base Damage = Skill Base Damage + (Added Damage × Damage Effectiveness)
```

**Key Points**:
- Damage Effectiveness varies by skill (100% default for most spells)
- Added damage from:
  - Support gems (e.g., "Added Lightning Damage Support")
  - Equipment (if applicable in PoE2)
  - Skill gem modifiers
- Spells multiply ONLY added damage by effectiveness (not base damage)

**Important Change from PoE1**:
PoE2 appears to lack weapon mods like "Adds 1-87 Lightning Damage to Spells", making gem levels more critical.

**Example**:
```
Base Damage: 100 (from gem level)
Added Damage: 50
Damage Effectiveness: 120%

Total = 100 + (50 × 1.2) = 100 + 60 = 160 base damage
```

**Source:** PoE Wiki, Maxroll.gg

---

### Archmage Support (Mana Scaling)

**Tier**: Spirit Gem

**Base Mechanic**:
- Non-Channelling spells cost additional mana
- Spells deal extra Lightning damage based on maximum Mana

**Damage Formula**:
```
Extra Lightning Damage = (Maximum Mana / 100) × 4%
```

**Recent Buff (Patch 0.3.0)**:
- Increased from 3% to 4% per 100 mana

**Characteristics**:
- Scales with Intelligence (increases max mana)
- Defense and offense from same stat
- Synergizes with:
  - Stormweaver ascendancy (Force of Will)
  - Mind Over Matter keystone
  - Mana stacking items

**Build Strategy**:
- Stack maximum mana as primary scaling stat
- Intelligence provides both mana and ES (defense)
- Mana becomes damage AND survivability

**Example**:
```
Maximum Mana: 2,500
Extra Damage = (2,500 / 100) × 4% = 25 × 4% = 100% of damage as extra Lightning

If base damage is 1,000:
Total = 1,000 + 1,000 = 2,000 damage
```

**Source:** poewiki.net, maxroll.gg Archmage build guides

---

## 5. Support Gem Interactions

### How Support Gems Work

**Primary Function**: Provide multiplicative "more" damage bonuses

**Tier System**:
- Higher-tiered support gems have higher values
- Secondary effects on some high-tier supports

**Stacking Formula**:
```
Total Multiplier = (1 + More1) × (1 + More2) × (1 + More3) × ...
```

**Example Support Gem Combinations**:
```
Support 1: 25% more spell damage
Support 2: 25% more spell damage
Support 3: 30% more spell damage

Total = 1.25 × 1.25 × 1.30 = 2.03125 (103% more damage)
```

**Key Principle**: Gaining additional sockets for support gems is extremely valuable because each provides multiplicative scaling.

**Damage Calculation Integration**:
Support gems are applied in the "More/Less" step of damage calculation, after increased/decreased modifiers.

**Source:** All PoE2 guides, support gem wikis

---

## 6. Critical Strike System

### PoE2 Changes from PoE1

**New System**: "Critical Damage Bonus" replaces "Critical Strike Multiplier"

**Base Values**:
- Default Critical Damage Bonus: +100%
- Total damage on crit: 200% (100% base + 100% bonus)
- PoE1 comparison: PoE1 had +50% default, PoE2 has +100%

### Critical Strike Chance

**Base Chance**: Listed on spell gem (varies by spell)
- Arc: Varies by level
- Spark: 9.00%
- Lightning Conduit: 10%
- Orb of Storms: Varies by level
- Ice Nova: 12.00%

**Crit Roll Mechanic**:
1. When skill is cast, random number rolled between 0-99.99
2. If Critical Strike Chance % exceeds this number, hit is critical
3. Same roll used for all hits from that cast

**Scaling**:
- "Increased Critical Hit Chance for Spells" (additive)
- Base crit chance modifiers (rare)

### Critical Damage Calculation

**Formula**:
```
Critical Multiplier = 1 + (Base Critical Damage Bonus + Added Critical Damage Bonus) × (1 + Increased Critical Damage) × (Product of More Critical Damage)
```

**Two Types of Scaling**:

1. **Increased Critical Damage Bonus** (more common)
   - Percentage-based increases/reductions
   - Stack additively with each other
   - Applied as multiplier to base bonus

2. **Added Critical Damage Bonus** (less common, more powerful)
   - Flat additions to critical damage bonus
   - Similar to PoE1's Critical Strike Multiplier
   - Added directly to base bonus

**Example Calculation**:
```
Base Critical Damage Bonus: +100%
Added Critical Damage Bonus: +41% (from flail)
Increased Critical Damage: 50%

Step 1: 100% + 41% = 141% base bonus
Step 2: 141% × (1 + 0.50) = 141% × 1.5 = 211.5%
Step 3: Total damage = 100% + 211.5% = 311.5% (3.115x)
```

### Expected DPS with Crits

**Formula**:
```
Expected DPS = (Base DPS × (1 - Crit Chance)) + (Base DPS × Critical Multiplier × Crit Chance)
```

**Example**:
```
Base DPS: 1,000
Crit Chance: 50%
Crit Multiplier: 3.0x

Non-crit contribution: 1,000 × 0.5 = 500
Crit contribution: 1,000 × 3.0 × 0.5 = 1,500
Expected DPS: 500 + 1,500 = 2,000
```

**Source:** Maxroll.gg, Mobalytics.gg Critical Hits Guide, PoE Wiki

---

## 7. Resistance and Penetration

### Resistance Mechanics

**Base Concept**: Resistance reduces damage by percentage
- Fire, Cold, Lightning, Chaos resistances
- Players and monsters both have resistances
- Cap varies (75% default for players in most cases)

**Formula**:
```
Damage Taken = Base Damage × (1 - Resistance%)
```

**Example**:
```
1,000 damage vs 75% resistance = 1,000 × 0.25 = 250 damage taken
1,000 damage vs 0% resistance = 1,000 × 1.0 = 1,000 damage taken
1,000 damage vs -50% resistance = 1,000 × 1.5 = 1,500 damage taken
```

### Penetration Mechanics

**Core Concept**: Penetration lowers effective resistance for YOUR damage calculation only

**Formula**:
```
Effective Resistance = min(Target Resistance, Max Resistance) - Penetration
```

**Key Limitations**:

1. **Cannot penetrate below 0%** (standard rule)
   - Wasted penetration if target has <0% resistance
   - Example: -25% resistance + 50% penetration = still -25% (25% penetration wasted)

2. **Exception**: Leopold's Applause Gloves
   - Only item allowing penetration below 0%
   - "Your Hits can Penetrate Elemental Resistances down to a minimum of -50%"

**Example Calculations**:
```
Target: 75% Fire Resistance
Penetration: 30%
Effective Resistance = 75% - 30% = 45%

Target: 20% Fire Resistance
Penetration: 30%
Effective Resistance = 20% - 30% = 0% (cannot go negative, 10% wasted)

Target: -10% Fire Resistance (from Exposure)
Penetration: 30%
Effective Resistance = -10% (penetration does nothing, all wasted)
```

### Exposure Mechanics

**Base Effect**: Debuff that reduces elemental resistance
- Default: -20% resistance for 4 seconds
- Can result in NEGATIVE resistances
- Applies to player or enemy

**Interaction with Penetration**:
Exposure is applied FIRST, then Penetration

**Order of Operations**:
1. Apply Exposure/Curses (can go negative)
2. Apply Penetration (cannot go below 0% normally)

**Example**:
```
Target: 75% Cold Resistance
Apply Frost Bomb Exposure: -50% → 75% - 50% = 25% resistance
Apply Penetration: 30% → 25% - 30% = 0% (limited to 0%)

Target: 75% Cold Resistance
Apply Exposure: -20% → 75% - 20% = 55% resistance
Apply Penetration: 40% → 55% - 40% = 15% resistance
Final damage: Base × (1 - 0.15) = Base × 0.85
```

### Negative Resistances

**When Exposure/Curses Alone Bring Below 0%**:
- Target takes INCREASED damage
- Penetration becomes useless (already below 0%)
- Better to use penetration OR exposure, not both when already negative

**Example**:
```
Target: 75% Fire Resistance
Exposure + Curses: -95% total reduction → 75% - 95% = -20% resistance
Damage = Base × (1 - (-0.20)) = Base × 1.20 (20% MORE damage)

Adding 30% penetration: Does nothing, resistance already negative
```

**Strategic Implication**: Penetration and negative resistances are mutually exclusive for maximum benefit.

**Source:** PoE Wiki Resistance Penetration, Mobalytics.gg Penetration Guide

---

## 8. Damage Conversion

### Core Mechanic

**Definition**: Changes damage type from one to another OR gains extra damage from existing type

**Two Categories**:

1. **Damage Conversion**: Changes type completely
2. **Damage Gain**: Adds extra damage without removing source

### Key Changes from PoE1

**MAJOR CHANGE**: Converted damage NO LONGER remembers source type

**Implication**:
- Old: Physical → Fire could scale with both Physical and Fire mods
- New: Physical → Fire scales ONLY with Fire mods

**Example**:
```
PoE1: 100 Physical converted to Fire
- Could scale with "increased Physical damage"
- Could scale with "increased Fire damage"
- Double dipping

PoE2: 100 Physical converted to Fire
- Scales ONLY with "increased Fire damage"
- Physical modifiers no longer apply
- No double dipping
```

### Conversion vs Gain

**Damage Conversion**:
```
"100% of Physical Damage Converted to Fire Damage"
- Physical damage becomes Fire damage
- Loses Physical scaling
- Gains Fire scaling
```

**Damage Gain**:
```
"Gain 50% of Physical Damage as Extra Fire Damage"
- Physical damage remains Physical
- Adds 50% of that value as Fire
- Physical still scales with Physical mods
- Fire portion scales with Fire mods
```

**Example**:
```
Base: 100 Physical Damage
Conversion (100% Phys → Fire): 100 Fire Damage
Gain (50% Phys as Fire): 100 Physical + 50 Fire

Conversion can scale with Fire mods only
Gain's Physical can scale with Phys mods, Fire can scale with Fire mods
```

### Two-Step Conversion Process

**Step 1**: Skill-inherent conversion
**Step 2**: All other conversion sources (gear, passives, etc.)

**Normalization**: If total conversion exceeds 100%, normalized to 100%

**Example**:
```
Conversion sources:
- 100% Physical → Fire (from passive)
- 50% Physical → Cold (from gear)

Total: 150% conversion
Normalized: 100% / 150% = 0.6667 multiplier
Final: 67% Fire, 33% Cold
```

### Limitations

**Only affects Hits**: Damage conversion and gain do NOT work for Damage over Time

**Calculated Before Scaling**: Conversion/Gain happens before damage modifiers apply

**Source:** PoE Wiki Damage Conversion, Mobalytics.gg Damage Conversion Guide

---

## 9. Special Mechanics

### Elemental Ailments

#### Shock
- **Effect**: 20% increased damage taken (debuff on enemy)
- **Duration**: 4 seconds (players), 8 seconds (non-players)
- **Stacking**: Does NOT stack, highest effect applies
- **Application Chance**: Based on damage dealt relative to enemy's ailment threshold
  - 25% chance per 100% of ailment threshold
- **Damage Bonus Calculation**: Applied multiplicatively in final damage

**Formula Integration**:
```
Final Damage = [...previous steps...] × (1 + 0.20 if shocked)
```

#### Chill
- **Effect**: Slows enemy action speed
- **Magnitude**: 30% minimum, 50% default maximum
- **Duration**: 2 seconds (players), 8 seconds (non-players)
- **Application**: Cold damage chills by default (no "chance to chill" needed)
- **Threshold**: Chills <30% magnitude are ignored
- **Scaling**: Based on cold damage relative to target's ailment threshold

#### Freeze
- **Effect**: Completely stops enemy movement and actions
- **Duration**: 4 seconds default
- **Application**: Cold hits that meet threshold
- **Scaling**: Damage modifiers (Shock, Exposure) improve freeze chance by improving hit damage

### Infusions

**Concept**: Elemental charges/buffs consumed by skills for enhanced effects

**Examples**:
- **Lightning Infusion**: Ember Fusillade consumes for chaining beams
- **Cold Infusion**: Spark fires in circle pattern with mixed damage
- **Fire Infusion**: Various skill modifications

**Generation**:
- Specific skills create Infusion Remnants
- Frost Bomb, Snap, Siphon Elements (Cold)
- Orb of Storms (Lightning when expired)

### Damage Effectiveness

**Spell Behavior**: Spells multiply ADDED damage by effectiveness

**Default**: 100% for most spells (not displayed)

**Formula**:
```
Total Base = Spell Base Damage + (Added Damage × Damage Effectiveness)
```

**Skills with Modified Effectiveness**: Usually displayed on gem if ≠ 100%

### Gem Level Scaling

**Importance**: Spell base damage scales with gem level

**Scaling Pattern**: Generally linear flat damage increases per level

**Priority**: +X to Spell Gem Levels is extremely valuable
- Directly increases base damage
- No diminishing returns like "increased damage"

**Example**:
```
+5 to Level of all Lightning Spell Gems
Arc level 15 → 20
Base damage: 100 → 150 (50% more base damage)
```

---

## 10. Official Sources

### Primary Resources

#### Official Wikis
- **PoE Wiki**: https://www.poewiki.net/wiki/poe2wiki:Damage
  - Community-maintained, GGG-supported
  - Most authoritative source
  - Damage conversion: https://www.poewiki.net/wiki/poe2wiki:Damage_conversion
  - Resistance penetration: https://www.poewiki.net/wiki/Resistance_penetration
  - Critical hits: https://www.poewiki.net/wiki/poe2wiki:Critical_hit

- **Fextralife Wiki**: https://pathofexile2.wiki.fextralife.com/
  - Individual spell pages
  - Good for quick reference

#### Database Sites
- **poe2db.tw**: https://poe2db.tw/us/
  - Datamined information
  - Spell stats, support gems
  - Most accurate for raw numbers
  - Spells list: https://poe2db.tw/us/ (navigate to Spells section)

### Community Guides

#### Maxroll.gg (Highly Recommended)
- **Damage Scaling Guide**: https://maxroll.gg/poe2/getting-started/damage-scaling
  - Comprehensive formulas
  - Clear examples
  - Order of operations

- **Build Guides**: https://maxroll.gg/poe2/build-guides/
  - Archmage Spark Stormweaver
  - Fireball builds
  - Ice Nova builds

#### Mobalytics.gg
- **Damage & Defence Order**: https://mobalytics.gg/poe-2/guides/damage-defence-calc-order
- **Penetration Guide**: https://mobalytics.gg/poe-2/guides/penetration
- **Resistances Guide**: https://mobalytics.gg/poe-2/guides/resistances
- **Critical Hits Guide**: https://mobalytics.gg/poe-2/guides/critical-hits
- **Freeze Guide**: https://mobalytics.gg/poe-2/guides/freeze

#### Other Resources
- **Game8**: https://game8.co/games/Path-of-Exile-2/archives/488221
  - Skill gem lists
  - Beginner guides

- **Sportskeeda**: https://www.sportskeeda.com/mmo/path-exile-2-poe2-sorceress-elemental-skills-gems
  - Sorceress spell lists

### Reddit Community
- **r/PathOfExile2** (subreddit likely exists but not directly searched)
- Community discussions
- Build sharing
- Mechanic testing

### GGG Official
- **Grinding Gear Games**: Official developer
- Patch notes on official forums
- Would have official mechanic explanations (not directly accessed in research)

---

## Implementation Notes for DPS Calculator

### Required Inputs

1. **Skill Information**:
   - Spell name
   - Gem level
   - Base damage range
   - Damage effectiveness
   - Critical strike chance
   - Cast time
   - Tags (Spell, Projectile, Area, etc.)

2. **Character Stats**:
   - % Increased Spell Damage (sum of all sources)
   - % More Spell Damage multipliers (list of each)
   - Flat added damage (by type)
   - Critical damage bonus (base + added + increased)
   - Cast speed increases
   - Maximum mana (for Archmage)

3. **Support Gems**:
   - List of support gems
   - Each gem's "more" multiplier
   - Each gem's added damage (if applicable)

4. **Enemy Stats**:
   - Resistances (Fire/Cold/Lightning/Chaos)
   - Ailment threshold
   - Applied debuffs (Shock, Exposure, Curses)

5. **Penetration/Reduction**:
   - % Resistance Penetration
   - Exposure amount
   - Curse effectiveness

### Calculation Steps (Code Implementation)

```typescript
// Step 1: Calculate base damage
const baseDamage = getSpellBaseDamage(gemLevel);

// Step 2: Add flat damage (with damage effectiveness)
const addedDamage = calculateAddedDamage(flatAddedDamage, damageEffectiveness);
const totalBaseDamage = baseDamage + addedDamage;

// Step 3: Apply increased/decreased (single additive sum)
const increasedMultiplier = 1 + (sumOfIncreased - sumOfDecreased);
const damageAfterIncreased = totalBaseDamage * increasedMultiplier;

// Step 4: Apply more/less (multiplicative stack)
const moreMultiplier = moreMultipliers.reduce((acc, more) => acc * (1 + more), 1);
const damageAfterMore = damageAfterIncreased * moreMultiplier;

// Step 5: Calculate expected damage with crits
const critMultiplier = 1 + calculateCritBonus(baseCritBonus, addedCritBonus, increasedCrit, moreCrit);
const nonCritDamage = damageAfterMore * (1 - critChance);
const critDamage = damageAfterMore * critMultiplier * critChance;
const expectedHitDamage = nonCritDamage + critDamage;

// Step 6: Apply resistance/penetration
const effectiveResistance = calculateEffectiveResistance(
  enemyResistance,
  exposure,
  penetration,
  curses
);
const damageAfterResistance = expectedHitDamage * (1 - effectiveResistance);

// Step 7: Calculate DPS
const castsPerSecond = calculateCastSpeed(baseCastTime, increasedCastSpeed);
const dps = damageAfterResistance * castsPerSecond;

// Special: Archmage scaling
if (hasArchmage) {
  const archmageBonus = (maxMana / 100) * 0.04; // 4% per 100 mana
  const extraLightningDamage = totalBaseDamage * archmageBonus;
  // Add to base damage and recalculate
}
```

### Special Considerations

1. **Arc Scaling**: Track remaining chains, apply 15% more per remaining chain
2. **Lightning Conduit**: Check if target is shocked, apply massive multiplier
3. **Spark**: Account for projectile count and hit frequency limitations
4. **Damage Conversion**: Apply before any scaling, track final damage type
5. **Infusion Mechanics**: May need toggle for "infusion consumed" state
6. **Quality Bonuses**: Additional chains, damage, etc.

### Validation

**Test Cases**:
- Basic spell with no modifiers
- Spell with increased damage only
- Spell with more multipliers
- Critical strike scenarios
- Resistance/penetration edge cases (negative resistance, penetration beyond 0%)
- Archmage with various mana pools
- Arc with different remaining chains
- Damage conversion scenarios

---

## Formulas Summary (Quick Reference)

### Core Damage Formula
```
Final Damage = (Base + Added × Effectiveness) × (1 + ΣIncreased) × Π(1 + More) × CritMultiplier × (1 - EffectiveRes)
```

### Critical Damage
```
CritMultiplier = 1 + (BaseCritBonus + AddedCritBonus) × (1 + IncreasedCrit) × Π(1 + MoreCrit)
```

### Effective Resistance
```
Step 1: Apply Exposure/Curses → TempRes = BaseRes - Exposure - Curses
Step 2: Apply Penetration → EffectiveRes = max(TempRes - Penetration, 0)
Exception: Leopold's Applause → min = -50% instead of 0%
```

### Expected DPS
```
ExpectedDPS = [(HitDmg × (1 - CritChance)) + (HitDmg × CritMult × CritChance)] × CastSpeed
```

### Archmage
```
ExtraLightningDmg = (MaxMana / 100) × 4%
```

### Damage Conversion Normalization
```
If ΣConversion > 100%:
  NormalizedConversion = (ConversionAmount / ΣConversion) × 100%
```

---

## Caveats and Special Cases

1. **Penetration Cannot Go Below 0%**: Except with Leopold's Applause unique gloves
2. **Negative Resistances**: Penetration is wasted if enemy already has negative resistance
3. **Conversion Lost Memory**: Converted damage doesn't scale with source type in PoE2
4. **Spell vs Attack Damage Effectiveness**: Spells multiply ONLY added damage; attacks multiply total
5. **Gem Levels Critical**: Spells scale base damage from gem level, not weapons
6. **Support Gem Sockets**: Each additional socket is exponential damage increase
7. **Increased vs More**: More multipliers are exponentially more valuable
8. **Ailment Threshold**: Boss enemies have much higher thresholds (harder to shock/freeze)
9. **Hit Rate Limitations**: Some skills (Spark) have same-target hit cooldowns
10. **Infusion Consumption**: One-time bonuses that require resource management

---

## Next Steps for Implementation

1. **Create Spell Database**:
   - JSON with all spell base stats by gem level
   - Include: base damage, crit chance, cast time, tags, special mechanics

2. **Build Modifier System**:
   - Categorize: increased, more, added damage, crit, cast speed
   - Proper stacking rules for each category

3. **Implement Calculation Pipeline**:
   - Follow exact order of operations
   - Modular functions for each step

4. **Add Resistance System**:
   - Exposure, penetration, curse calculations
   - Proper ordering and limitations

5. **Special Mechanics**:
   - Arc remaining chains
   - Lightning Conduit shock multiplier
   - Archmage mana scaling
   - Damage conversion

6. **Support Gem Library**:
   - Database of all support gems
   - Their more multipliers and effects

7. **Testing Framework**:
   - Unit tests for each formula
   - Integration tests for full builds
   - Validation against known builds

8. **User Interface**:
   - Input fields for all modifiers
   - Spell selection
   - Support gem selection
   - Real-time calculation updates

---

**End of Research Document**

*This document synthesizes information from multiple authoritative sources as of 2025-10-23. Path of Exile 2 is in Early Access and mechanics may change with patches. Always verify against latest patch notes and official sources.*

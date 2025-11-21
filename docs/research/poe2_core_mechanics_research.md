# Path of Exile 2 Core Mechanics - Comprehensive Research

**Research Date:** 2025-10-22
**Sources:** www.poe2wiki.net, pathofexile2.wiki.fextralife.com
**Status:** Path of Exile 2 Early Access

---

## Table of Contents
1. [Damage Calculation System](#damage-calculation-system)
2. [Defense Mechanics](#defense-mechanics)
3. [Combat Mechanics](#combat-mechanics)
4. [Ailment System](#ailment-system)
5. [Critical Strike Mechanics](#critical-strike-mechanics)
6. [Resource Systems](#resource-systems)
7. [New PoE2-Specific Mechanics](#new-poe2-specific-mechanics)
8. [Key Differences from PoE1](#key-differences-from-poe1)
9. [Numeric Constants Reference](#numeric-constants-reference)

---

## Damage Calculation System

### Order of Operations (11 Steps)

Path of Exile 2 uses a precise 11-step damage calculation process:

#### Step 1: Avoiding the Hit
Defensive mechanics that completely prevent hits:
- Manual movement avoidance
- Dodge roll i-frames (projectiles and non-AoE attacks only)
- Projectile avoidance mechanics
- Evasion vs. accuracy checks

**Important:** These are the ONLY mechanics that prevent on-hit effects from triggering.

#### Step 2: Before Being Hit
Effects like "Recover #% of Missing Life before being Hit" activate after failed hit prevention but before damage calculation.

#### Step 3: Calculating Unmitigated Damage

##### Flat Damage Calculation
```
Foundation Damage = Base Damage + Added Damage
```
All flat damage additions are summed additively.

##### Damage Conversion (Two-Step Process)

**Step 1 - Skill-based conversion:**
- Conversions from skill gems
- Item-granted skill conversions
- Ascendancy passive conversions

**Step 2 - Global/conditional conversion:**
- Support gem conversions
- Item modifier conversions
- Buff conversions
- Passive skill conversions

**Critical Rule:** "Regular conversion exceeding 100% of any original damage type is scaled down to 100%."

**Timing:** Conversion occurs AFTER combining added damage but BEFORE damage multipliers.

##### Damage Multipliers

**Increased/Reduced modifiers (additive):**
```
Increased Modifier = (1 + ΣIncreased - ΣReduced)
```

**More/Less modifiers (multiplicative):**
```
More Multiplier = Π(1 + More) × Π(1 - Less)
```
Applied independently unless from the same source.

##### Critical Hits
```
Default Critical Damage = Base Damage × 2.0 (200% total)
Critical Damage Bonus = +100% (can be modified)
```

Can be reduced by "Take #% reduced Extra Damage from Critical Hits"

##### Rolling for Damage
After multipliers apply to min/max range, damage randomly selects within that range.
- **Lucky damage:** Rolls twice, uses higher value
- **Unlucky damage:** Rolls twice, uses lower value

##### Doubling/Tripling Damage
Applies AFTER all other offensive modifiers.

#### Step 4: Cannot Take Damage
Modifiers that remove damage entirely before mitigation (e.g., "Cannot take Reflected Physical Damage").

#### Step 5: Damage Taken As (Shift)
Converts incoming damage to different type.

**Key Mechanics:**
- "Damage types can only be shifted once"
- "All damage shift effects apply simultaneously"
- "Shifted damage is only affected by mitigation for its final damage type"

#### Step 6: Damage Mitigation (Order of Application)

1. Cannot take X damage (second application)
2. Immunities (100% prevention)
3. Avoidance (chance-based prevention)
4. Damage reduction (from armour)
5. Resistance (elemental/chaos mitigation)

**CRITICAL DIFFERENCE FROM POE1:** "Damage reduction occurs before resistances, unlike in POE1."

##### Armor Damage Reduction Formula
```
DR(A, D_raw) = A / (A + 10 × D_raw)
```

Where:
- A = defender's armor rating
- D_raw = raw physical damage from the hit

##### Required Armor for Target DR
```
A(D_raw, DR) = (DR × 10 × D_raw) / (1 - DR)
```

**Armor Limitations:**
- Maximum damage reduction: 90% (from all sources)
- Armor can prevent maximum of 1/5 of its value per hit
- Does NOT work against damage over time

**Rules of Thumb:**
- 33% reduction: 5× incoming damage
- 50% reduction: 10× incoming damage
- 66% reduction: 20× incoming damage
- 75% reduction: 30× incoming damage
- 90% reduction: 90× incoming damage

##### Evasion Chance to Hit Formula
```
Uncapped Chance to Hit = (Attacker's Accuracy × 1.25 × 100) / (Attacker's Accuracy + Defender's Evasion × 0.3)
```

**Constraints:**
- Minimum hit chance: 5%
- Maximum evade chance: 95%

**Entropy System:**
Evasion uses deterministic entropy rather than pure RNG:
1. Entropy value randomizes 0-99 on first attack or after 3.33+ seconds idle
2. Each attack adds its hit chance % to entropy
3. When entropy ≥100: attack hits, subtract 100 from entropy
4. When entropy <100: attack evades

This ensures predictable hit patterns: N% hit chance = exactly 1 hit per N attacks.

##### Resistance Formula
```
Final Damage = D × (100 - R) / 100
```

**Resistance Caps:**
- Default maximum: 75%
- Hard cap: 90% (cannot be exceeded)

**Resistance Penalties:**
| Stage | Penalty |
|-------|---------|
| Act 2 | -10% |
| Act 3 | -20% |
| Act 4 | -30% |
| Area Level 54-59 | -40% |
| Area Level 60-64 | -50% |
| Area Level 65+ | -60% |

#### Step 7: Modifying Damage Taken

Order of application:
1. Flat modifiers (±# X Damage taken)
2. Increases/reductions (summed)
3. More/less multipliers (applied independently)

#### Step 8: Stun and Ailment Thresholds
Chance/buildup rolled based on current damage value.

#### Step 9: Blocking
Block prevents all damage or percentage thereof.
- Blocks most on-hit effects
- Does NOT block stun/freeze effects

#### Step 10: Final Damage Taken
Reference point for prevented damage calculations (excludes block mitigation).

#### Step 11: Applying Damage and Losing Resources

##### Resource Depletion Order
1. Other entity effects/buffs (multiplicative)
2. Energy shield
3. Mana (if applicable via mechanics)
4. Life

**Special Rules:**
- "Chaos Damage inherently removes twice as much energy shield as the damage value"
- Bleeding and Poison bypass energy shield, damage life directly
- Life loss prevention effects are multiplicative, not additive

### Damage Over Time

"Damage over time does not hit, bypassing many hit-based defensive mechanics."

Ailment damage calculated as "percentage of the hit's damage before mitigations," preventing double-scaling from multipliers.

---

## Defense Mechanics

### Armor

**Core Function:** Reduces physical damage from hits only (not DoT).

**Formula:**
```
DR(A, D_raw) = A / (A + 10 × D_raw)
```

**Key Constants:**
- Armor scaling factor: 10
- Maximum DR: 90%
- Damage cap: 1/5 of armor value per hit

**Effectiveness:** More effective against many small hits than few large hits.

**Attribute:** Scales with Strength

### Evasion Rating

**Core Function:** Grants chance to evade enemy hits.

**Formula:**
```
Uncapped Chance to Hit = (Attacker's Accuracy × 1.25 × 100) / (Attacker's Accuracy + Defender's Evasion × 0.3)
```

**Key Constants:**
- Evasion multiplier: 0.3
- Accuracy multiplier: 1.25
- Minimum hit chance: 5%
- Maximum evade chance: 95%

**Entropy Reset:** 100 server ticks (3.33 seconds) of inactivity

**Critical Hit Mechanics:** If attack would be critical but evaded, evasion is tested again independently to potentially downgrade to normal hit.

**Attribute:** Scales with Dexterity

### Energy Shield

**Core Definition:** "Energy Shield protects your Life by taking damage instead."

**Recharge Mechanics:**
```
Base Recharge Rate = 12.5% of maximum ES per second
Base Recharge Delay = 4 seconds

Faster Start Formula:
Delay Period = 400 / (100 + r)
```
Where r = sum of "faster start of Energy Shield Recharge" modifiers as percentage

**Example:** With 100% faster start: 400/200 = 2 second delay

**Special Interactions:**
- Chaos damage removes 2× as much ES
- Bleeding and Poison bypass ES entirely, damage life directly
- Recharge is interrupted by ANY damage to Life or ES
- Recharge is recovery but NOT regeneration

**Attribute:** Scales with Intelligence

### Block Mechanics

**Core Effect:** "Blocking completely prevents the damage of an incoming Hit."

**Important:** Players still receive Stun and Freeze debuffs despite damage negation.

#### Passive Block
- Applied to blockable hits from ANY direction
- Primary source: shields
- Maximum cap: 50% (changed from 75% in v0.3.0)
- Rounds to nearest integer
- Does NOT build Heavy Stun meter

#### Active Block
Skills like Raise Shield, Parry, Shield Charge provide directional guaranteed blocks.
- Builds Heavy Stun meter
- Meter fills → cancels and stuns player for 3 seconds
- Must face enemy (v0.3.0 change)

**Restrictions:**
- Cannot block while Stunned or Frozen
- Boss skills with red flash are unblockable
- Damage over time cannot be blocked
- "Blocked damage is not considered 'prevented damage'" for specific mechanics

**Version Changes:**
- v0.3.0: Max block reduced from 75% to 50%
- v0.2.0: Active block grants evasion-equal heavy stun avoidance chance
- v0.1.0d: Passive block applies from all directions

---

## Combat Mechanics

### Movement & Controls

**WASD Control Scheme:** Enables simultaneous movement and ability use (new for PoE2).

### Dodge Roll (NEW TO POE2)

**Distance:** 3.7 metres in selected direction
**Cooldown:** None (by default)
**Cost:** None (by default)

**Invincibility Frames:**
- First half of animation avoids damage from projectiles and non-AoE attacks
- Does NOT avoid AoE or boss slam attacks
- Enables animation cancellation of most skills

**Size Reduction:** Character size reduced to 0 units during animation

**Modifiers:**
- Distance scales with movement speed (as speed, not duration extension)
- Cannot cross gaps or terrain obstacles
- Can push small monsters

**Special Interactions:**
- Bulwark keystone: Removes i-frames, grants consistent damage reduction
- Ab Aeterno (unique): "Dodge Roll avoids all Hits"

### Sprint Mechanic (NEW TO POE2)

**Activation:** Hold dodge roll button after initial dodge animation

**Effects:**
- Faster out-of-combat movement
- No stamina cost
- "When a monster or an enemy hits them, they will get knocked down"

### Stun System

#### Light Stun
- Brief interruption triggered by hit damage
- Chance scales up to 100% for hits dealing damage equal to target's max life
- Any chance below 15% is treated as 0%

#### Heavy Stun (NEW TO POE2)
- Longer duration when stun bar fills completely
- Buildup accumulates from hits
- Decreases over time if no buildup occurs

**Stun Threshold:**
- Player base threshold = maximum life
- Increasing threshold reduces light stun chance and heavy stun buildup

**Damage Type Bonuses (Players):**
- Physical damage: 50% more stun
- Melee damage: 50% more stun
- Physical melee: 125% total (multiplicative)

**Damage Type Bonuses (Monsters):**
- Physical damage: 100% more stun
- Melee damage: 33% more stun
- Physical melee: 166% total (multiplicative)

**Player-Specific Rules:**
Players cannot be directly heavy stunned except:
- Raising shields
- Parrying with bucklers
- Riding mounts
- Being hit while sprinting

**Heavy Stun Duration:** 3 seconds (cannot evade or block)

**Related Mechanics:**
- Primed for Stun: 40-70% heavy stun buildup (varies by enemy rarity)
- Daze: Hits apply 50% more stun buildup
- Crushing Blows: Heavy stun on enemies primed for stun

### Deflect System (NEW TO POE2)

**Core Mechanic:** "Successfully deflect a hit" grants "40% less damage from the attack"

**Scaling:** Scales with evasion-based items and passive skill tree investment

**Key Constant:** 40% damage reduction on successful deflect

### Accuracy

**Base Accuracy Values:**
- +6 base accuracy per player level
- +6 base accuracy per point of dexterity

**Formula:**
```
Uncapped Chance to Hit = (Attacker's Accuracy × 1.25 × 100) / (Attacker's Accuracy + Defender's Evasion × 0.3)
```

**Constraints:**
- Minimum: 5%
- Maximum: 100% (125% with specific modifiers like Amazon's Critical Strike)

**Distance Penalty (Players):**
- 0-2 metres: No penalty
- 2-9 metres: Linear increase in penalty
- 9+ metres: Maximum 90% reduced accuracy

**Special Cases:**
- "Can't be Evaded" or "Always Hit": Bypass accuracy/evasion
- Spells: Do not benefit from accuracy
- Player minions: Always hit with attacks

### Skill Speed

**Formula:**
```
usetime_Final = (usetime_Base / (1 + (skillspeed% / 100))) + usetime_Penalty
```

**Variants:**
- Attack speed (attacks and crossbow reload)
- Cast speed (spells)
- Throw speed (traps)
- Summon speed (totems)
- Warcry speed (warcries)
- Reload speed (crossbows)

All variants stack additively with general skill speed.

**Performance Limitation:**
- Server frame: 33 milliseconds
- Maximum actions: ~30.3 per second
- Skills reduced below 0.033 seconds may lose DPS

**Use Time Penalties:**
Some skills have inherent penalties added AFTER speed modifiers (cannot be modified by speed stats).

---

## Ailment System

### Ailment Threshold

**Player Base Threshold:** Half of maximum life (changed from full life in v0.2.0)

**Unique Monsters:** May have reduced relative thresholds for extremely large life pools

### Damaging Ailments

#### Bleeding

**Duration:** 5 seconds (default)

**Base Magnitude:**
```
Bleeding DPS = 15% of Pre-mitigation Physical damage per second
```

**Contributing Damage:** Physical only

**Special Mechanics:**
- Deals 100% additional damage while target moves or if Aggravated
- Bypasses Energy Shield, damages Life directly
- Requires explicit Bleeding chance source (damage alone doesn't apply)

**v0.2.0e Change:** Now considers damage to ES/Mana, not just life

#### Poison

**Duration:** 2 seconds (default)

**Base Magnitude:**
```
Poison DPS = 20% of Pre-mitigation Physical and Chaos damage per second
```

**Contributing Damage:** Physical and Chaos

**Mechanics:**
- Bypasses Energy Shield, damages Life directly
- Deals Chaos damage over time
- Requires explicit Poison chance source

#### Ignite

**Duration:** 4 seconds (default)

**Base Magnitude:**
```
Ignite DPS = 20% of Fire damage dealt by the Hit per second
```

**Contributing Damage:** Fire only

**Chance:** Determined by total Flammability on target

**v0.2.0e Change:** Spread delay reduced from 2 to 1 second

### Non-Damaging Ailments

#### Chill

**Duration:**
- Players: 2 seconds
- Non-players: 8 seconds

**Magnitude:**
```
Effect = 1/2 × (D/T)^0.4 × (1 + M)

Minimum: 30%
Default Maximum: 50%
```

Where:
- D = Chilling damage
- T = Ailment threshold
- M = Chill effect modifiers

**Application:** "Will always be applied" if damage meets minimum threshold

**Contributing Damage:** Cold (automatic, no chance required)

**Damage Requirements:**
- 5% chill: 0.32% of ailment threshold
- 10% chill: 1.79% of ailment threshold
- 20% chill: 10.12% of ailment threshold
- 30% chill: 27.89% of ailment threshold

#### Freeze

**Duration:** 4 seconds (default)

**Mechanism:** Buildup system - Cold damage accumulates until target becomes Frozen

**Contributing Damage:** Cold only

**Interaction:** Layered buildup mechanics - "enemies require a buildup of freeze effects before they can be fully frozen"

#### Shock

**Duration:**
- Players: 4 seconds
- Non-players: 8 seconds

**Effect:** "Causes targets to take 20% increased damage"

**Chance Formula:**
```
Shock Chance = 1% per 4% of target's Ailment Threshold dealt
```

**Contributing Damage:** Lightning only

**Fixed Effect:** 20% increased damage taken (not variable like PoE1)

#### Electrocute

**Duration:** 5 seconds (default)

**Mechanism:** Buildup system

**Effect:** Action speed becomes 0 (immobilization)

**Contributing Damage:** Lightning from specific skills/effects only

### Damage Contribution Rules

"By default, specific Ailments are calculated based on only specific damage types."

Allowing additional damage types: "All damage of the relevant types is summed when performing calculations."

For magnitude-only ailments (Bleeding, Poison): "You still need a way to apply those Ailments" despite damage contribution.

---

## Critical Strike Mechanics

### Default Critical Damage

**Base Critical Damage Bonus:** +100% (200% total damage)

**Formula:**
```
Critical Hit Damage = Base Damage × (1 + Critical Damage Bonus)
Default = Base Damage × 2.0
```

**Monster Critical Damage:** 40% less bonus = 60% critical damage bonus (160% total)

### Critical Hit Chance Calculation

**Base Values by Skill Type:**
- Attacks: Use weapon's base critical hit chance
- Unarmed attacks: 5% base
- Spells: Base listed on skill gem

**Modifier Application Order:**
1. Additive base critical hit chance modifiers ("+#% to Critical Hit Chance")
2. Percentage-based modifiers (increased/decreased/more/less)

**Example:** 100% increased crit on 7% base = 14% final crit chance

### Critical Hit Check Process

System rolls 0 to 99.99 to determine threshold. Skill's crit chance must exceed roll to trigger critical.

### Critical Damage Bonus Formula

1. Add flat +#% modifiers to base +100%
2. Apply multiplicative modifiers (increased/decreased/more/less)

This is a unique multiplier independent of all other damage multipliers.

### Key Terminology

PoE2 uses "critical damage bonus" (equivalent to PoE1's "critical strike multiplier" or "crit multi").

---

## Resource Systems

### Life

**Base Starting Value:** 28 life at level 1 (before bonuses)

**Growth Formula:**
```
Maximum Life = 28 + (12 × Player Level) + (2 × Strength)
```

**Low Life Threshold:** 35% of maximum life or lower

**Full Life:** 100% of maximum life or higher (unless reserved)

**Recovery:** Full restoration when entering town or hideout

### Mana

**Base Starting Value:** 34 mana at level 1 (before intelligence)

**Growth Formula:**
```
Maximum Mana = 34 + (4 × Player Level) + (2 × Intelligence)
```

**Base Regeneration:** 4% of maximum mana per second (does not scale with level)

**Low Mana Threshold:** 35% of maximum mana or lower

**Full Mana:** 100% of maximum mana or higher (unless reserved)

**Skill Mechanics:**
- Most skills consume mana throughout duration (not just on cast)
- Canceling or being stunned does not consume mana
- Default attacks cost no mana

### Energy Shield

**Recharge Rate:** 12.5% of maximum ES per second

**Recharge Delay:** 4 seconds (base)

**Faster Start Formula:**
```
Delay Period = 400 / (100 + r)
```
Where r = sum of "faster start" modifiers

**Chaos Damage:** Removes 2× as much ES as damage value

**Bypassed By:** Bleeding and Poison (damage Life directly)

### Spirit (NEW TO POE2)

**Definition:** "Spirit is a reserve of power used to activate and maintain skills with permanent effects."

**How to Gain Spirit:**

Quest Rewards:
- Gembloom Skull (Act 1): +30 Spirit
- Gemrot Skull (Act 3): +30 Spirit
- Gemcrust Skull (Interlude 3): +40 Spirit
- **Maximum from quests:** 100 Spirit

Equipment Sources:
- Sceptres
- Body armours
- Amulets
- Unique items (Enfolding Dawn: +100, Alpha's Howl: +100)

**What Consumes Spirit:**
- Persistent buff activation
- Permanent minion summoning
- Trigger meta gem enablement

**Special Rule:** "Persistent buffs and permanent minions granted by items or ascendancy passive skills do not reserve spirit."

**Notable Modifiers:**
- Prism Guardian: "+1 to Maximum Spirit per 25 Maximum Life"
- Matsya: "Skills reserve 50% less Spirit"
- Kaom's Heart: "You have no Spirit"

---

## New PoE2-Specific Mechanics

### 1. Dodge Roll
- 3.7 metre movement
- I-frames during first half of animation
- No cooldown or cost
- Character size reduced to 0 during animation

### 2. Sprint
- Activated by holding dodge roll button
- No stamina cost
- Knocked down when hit

### 3. Heavy Stun System
- Visible stun bar beneath enemy health
- Builds from hits, decreases over time
- Players only vulnerable in specific situations

### 4. Deflect
- 40% less damage on successful deflect
- Scales with evasion

### 5. Spirit Resource
- New resource for persistent effects
- Gained from quests and equipment
- Used for buffs, permanent minions, triggers

### 6. WASD Movement
- Simultaneous movement and ability use
- Fundamental control change from PoE1

### 7. Blockable Everything
- "Everything is now blockable except for a specific unblockable red flash skill that bosses use"
- Significant change from PoE1

### 8. Layered Ailment Buildup
- Freeze requires buildup
- Electrocute uses buildup
- More strategic ailment application

### 9. Fixed Shock Value
- Shock = 20% increased damage taken
- No scaling based on damage dealt
- Simplified from PoE1

---

## Key Differences from PoE1

### Damage Calculation
1. **Armor applies BEFORE resistances** (reversed from PoE1)
2. Damage over time cannot be converted
3. Damage shift can only occur once per damage type

### Defense Mechanics
1. **Block cap reduced to 50%** (from 75%)
2. Energy Shield chaos damage multiplier: 2× (specific to PoE2)
3. Evasion entropy resets after 3.33 seconds
4. Everything is blockable except red flash boss skills

### Ailment System
1. **Shock is fixed at 20%** (not variable based on damage)
2. **Player ailment threshold = 50% of max life** (not 100%)
3. **Freeze uses buildup system** (not duration based on hit)
4. **Bleeding bypasses ES** (different from PoE1)
5. **Poison bypasses ES** (different from PoE1)
6. Ignite spread delay: 1 second (reduced from 2)

### Critical Strikes
1. Terminology: "Critical Damage Bonus" (vs "Critical Strike Multiplier")
2. Mechanics largely similar but terminology updated

### Resource Systems
1. **Spirit resource** (completely new)
2. **Mana consumed throughout skill duration** (not just on cast)
3. Skills cancelled or interrupted don't consume mana

### Combat Mechanics
1. **Dodge roll** (completely new)
2. **Sprint** (completely new)
3. **WASD controls** (completely new)
4. **Heavy Stun system** (completely new)
5. **Deflect** (completely new)
6. **Stun visible bar** (new UI element)

### Resistance System
1. Penetration works only on positive resistances
2. "Ignore Resistance" calculates as if 0%
3. Exposure stacks with curses and penetration

---

## Numeric Constants Reference

### Damage Calculation
- **Critical Damage Bonus:** +100% (200% total)
- **Monster Critical Bonus:** +60% (160% total)
- **Armor Scaling Factor:** 10
- **Maximum Armor DR:** 90%
- **Armor Cap Ratio:** 1/5 of armor value per hit

### Evasion & Accuracy
- **Evasion Multiplier:** 0.3
- **Accuracy Multiplier:** 1.25
- **Minimum Hit Chance:** 5%
- **Maximum Evade Chance:** 95%
- **Entropy Reset Time:** 3.33 seconds
- **Base Accuracy per Level:** +6
- **Base Accuracy per Dexterity:** +6
- **Distance Penalty Start:** 2 metres
- **Distance Penalty End:** 9 metres
- **Maximum Distance Penalty:** 90%

### Energy Shield
- **Base Recharge Rate:** 12.5% per second
- **Base Recharge Delay:** 4 seconds
- **Faster Start Constant:** 400
- **Chaos Damage Multiplier:** 2×

### Resistances
- **Default Cap:** 75%
- **Hard Cap:** 90%
- **Endgame Penalty:** -60%
- **Default Exposure:** 20% for 4 seconds

### Block
- **Passive Block Cap:** 50%
- **Deflect Damage Reduction:** 40%
- **Heavy Stun Duration:** 3 seconds

### Ailments
**Bleeding:**
- Duration: 5 seconds
- DPS: 15% of pre-mitigation physical

**Poison:**
- Duration: 2 seconds
- DPS: 20% of pre-mitigation phys/chaos

**Ignite:**
- Duration: 4 seconds
- DPS: 20% of fire damage

**Chill:**
- Duration (Players): 2 seconds
- Duration (Monsters): 8 seconds
- Minimum: 30%
- Maximum: 50%

**Freeze:**
- Duration: 4 seconds

**Shock:**
- Duration (Players): 4 seconds
- Duration (Monsters): 8 seconds
- Effect: 20% increased damage taken
- Chance: 1% per 4% of ailment threshold

**Electrocute:**
- Duration: 5 seconds

### Resources
**Life:**
- Base: 28
- Per Level: +12
- Per Strength: +2
- Low Life: 35%

**Mana:**
- Base: 34
- Per Level: +4
- Per Intelligence: +2
- Base Regen: 4%
- Low Mana: 35%

**Spirit:**
- Quest Maximum: 100
- Gembloom: +30
- Gemrot: +30
- Gemcrust: +40

### Combat
- **Dodge Roll Distance:** 3.7 metres
- **Server Frame:** 33 milliseconds
- **Max Actions/Second:** ~30.3
- **Light Stun Minimum:** 15% chance

### Stun Bonuses
**Players:**
- Physical: 50% more
- Melee: 50% more
- Physical Melee: 125% total

**Monsters:**
- Physical: 100% more
- Melee: 33% more
- Physical Melee: 166% total

---

## Formula Quick Reference

### Armor Damage Reduction
```
DR = A / (A + 10 × D_raw)
Required Armor = (DR × 10 × D_raw) / (1 - DR)
```

### Evasion/Accuracy
```
Hit Chance = (Attacker Accuracy × 1.25 × 100) / (Attacker Accuracy + Defender Evasion × 0.3)
```

### Resistance
```
Final Damage = D × (100 - R) / 100
```

### Energy Shield Recharge
```
Recharge Rate = 12.5% per second
Delay = 400 / (100 + faster_start_%)
```

### Skill Speed
```
Final Use Time = (Base Use Time / (1 + speed%/100)) + Penalty
```

### Critical Damage
```
Critical Damage = Base × (1 + Critical Damage Bonus)
Default = Base × 2.0
```

### Ailment Magnitude (Chill)
```
Effect = 1/2 × (Damage / Threshold)^0.4 × (1 + Modifiers)
```

### Shock Chance
```
Shock Chance% = Damage / (Ailment Threshold × 0.04)
```

### Maximum Life/Mana
```
Max Life = 28 + (12 × Level) + (2 × Strength)
Max Mana = 34 + (4 × Level) + (2 × Intelligence)
```

---

## Research Notes

**Primary Differences Identified:**
1. Armor before resistance (major change)
2. Block cap reduced significantly
3. Fixed shock value (simplified)
4. Ailment threshold halved for players
5. Completely new mechanics: Dodge Roll, Sprint, Spirit, Heavy Stun, Deflect
6. WASD movement system
7. ES bypassed by Bleeding/Poison
8. Freeze buildup system

**Missing Information:**
- Detailed formulas for Heavy Stun buildup rate
- Exact Deflect scaling with evasion investment
- Comprehensive list of all unblockable attacks
- Detailed ailment buildup thresholds
- Complete Spirit scaling formulas
- Exact dodge roll i-frame timing (frame data)

**Sources Consulted:**
- www.poe2wiki.net (primary source)
- pathofexile2.wiki.fextralife.com (supplementary)
- Multiple individual mechanic pages
- Version history notes where available

**Research Limitations:**
- Path of Exile 2 is in Early Access
- Some mechanics may change
- Some wiki pages returned 404 errors
- Not all formulas have been datamined
- Some mechanics are estimated from player testing

---

## Version History Noted

**v0.3.0:**
- Maximum block reduced from 75% to 50%
- Shield modifiers reduced from 7 to 3
- Active blocking requires facing enemy

**v0.2.0:**
- Player Ailment Threshold changed to 50% of max life (from 100%)
- Active block grants evasion-equal heavy stun avoidance

**v0.2.0e:**
- Bleeding considers ES/Mana damage
- Ignite spread delay reduced to 1 second

**v0.1.0d:**
- Passive block applies from all directions

---

**Document Status:** Based on Early Access information as of 2025-10-22. Subject to change as game develops.

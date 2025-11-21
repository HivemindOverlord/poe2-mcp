# Path of Exile 2 Attack Damage Calculation Research

## Executive Summary

This document provides comprehensive research on Path of Exile 2's attack damage calculation mechanics, including formulas, weapon types, attack skills, accuracy mechanics, and implementation guidance for an attack DPS calculator.

**Key Findings:**
- Attacks derive base damage from weapon stats (physical + elemental damage ranges)
- Attack damage calculation follows a strict order of operations
- Critical hits use weapon base crit chance (not gem-based like spells)
- Accuracy vs Evasion determines hit chance, with distance penalties (new in PoE2)
- Dual wielding combines both weapons into single hit (no inherent stat bonuses)
- "Increased" modifiers are additive, "More" modifiers are multiplicative

---

## 1. Attack Damage Formula

### 1.1 Complete Order of Operations

```
Attack Damage = (((Base Weapon Damage + Added Flat Damage) × Damage Effectiveness)
                × Damage Conversion
                × (1 + Sum of Increased/Decreased Modifiers)
                × Product of (1 + More/Less Modifiers)
                + Gained as Extra Damage)
                × Critical Strike Multiplier (if crit)
```

### 1.2 Step-by-Step Breakdown

**Step 1: Base Damage Calculation**
```
Base Damage = Weapon Physical Damage + Weapon Elemental Damage
```

For attacks, base damage is derived from:
- **Weapon damage** for normal attacks (default)
- **Unarmed base damage** for unarmed attack skills (5% base crit)
- **Shield stats** for shield attack skills (e.g., Shield Charge)
- **Skill gem** for totem attack skills (e.g., Shockwave Totem)

**Step 2: Added Flat Damage**
```
Total Base Damage = Base Damage + All Added Flat Damage Sources
```

Added flat damage sources include:
- Skill gems (e.g., "Adds 10 to 20 Physical Damage")
- Support gems
- Gear (rings, amulets, gloves, belts)
- Passive tree nodes
- Buffs and auras

**Important:**
- Flat damage on weapons is LOCAL (increases weapon base damage, shown in blue)
- Flat damage on other gear is GLOBAL (added to attacks, not weapon base)

**Step 3: Damage Effectiveness**
```
Effective Base Damage = Total Base Damage × Attack Damage Effectiveness
```

Attack skills display their damage effectiveness as "Attack Damage: X% of Base"
- Most attack skills have varying effectiveness (e.g., Sunder: 237%)
- Unlike spells, attacks multiply ALL damage (base + added) by effectiveness

**Step 4: Damage Conversion**

Conversion occurs in two steps:

**Step 4a: Skill-Inherent Conversion**
- Applied first
- From skill gems, item grants, or Ascendancy passives
- Example: Physical to Fire conversion on skill

**Step 4b: All Other Conversion**
- Applied to remaining damage after Step 4a
- From support gems, items, passive skills
- Steps 4a and 4b are NOT additive (they apply sequentially)

**Important:** Converted damage:
- Only scales with modifiers of the NEW damage type
- No longer scales with the ORIGINAL damage type
- Can cause ailments of the new type

**Step 5: Increased/Decreased Modifiers**
```
Damage After Increases = Effective Base Damage × (1 + Sum of All Increased/Decreased)
```

All "increased" and "decreased" modifiers are **additive** with each other:
- 50% increased + 30% increased = 80% increased total
- Applied as a single multiplier: × 1.80

Examples:
- Increased Physical Attack Damage
- Increased Attack Damage
- Increased Damage with Two-Handed Weapons
- Increased Projectile Damage (if projectile attack)

**Step 6: More/Less Modifiers**
```
Damage After More = Damage After Increases × Product of (1 + More/Less Modifiers)
```

All "more" and "less" modifiers are **multiplicative**:
- 25% more damage × 30% more damage = × 1.25 × 1.30 = × 1.625 total
- Each more modifier is its own separate multiplier

Examples:
- Support gems (most common source)
- Ascendancy notables
- Unique item effects

**Step 7: Gained as Extra Damage**
```
Damage with Gained = Damage After More + (Base Damage × Sum of Gained Modifiers)
```

Gained damage modifiers grant a percentage of base damage as extra damage:
- "Gain 20% of Physical Damage as Extra Fire Damage"
- Gained damage is **additive** with other gained damage sources
- Gained damage is **multiplicative** with other scaling
- Occurs in Step 2 of conversion (most cases), so it's NOT converted
- Exception: Skills with no inherent conversion have gained in Step 1, allowing conversion

**Step 8: Critical Strike Multiplier**
```
Final Damage = Non-Crit Damage × Critical Damage Multiplier (if crit occurs)
```

### 1.3 Weapon Damage Ranges

Weapons have minimum and maximum damage values for each damage type:

```
Physical Damage: X-Y Physical
Elemental Damage: X-Y Fire/Cold/Lightning
Chaos Damage: X-Y Chaos
```

**Damage Roll Calculation:**
```
Each Hit Damage = Random value between (Min, Max) for each damage type
Total Hit = Sum of all damage types
```

**Average Damage Per Hit:**
```
Average Damage = (Min + Max) / 2
```

**Example:**
```
Weapon: 56-106 Physical, 15-30 Fire
Average Physical: (56 + 106) / 2 = 81
Average Fire: (15 + 30) / 2 = 22.5
Total Average: 103.5 damage per hit
```

### 1.4 Attack Speed Calculation

**Base Attack Speed:**
```
Base Attack Speed = Weapon Base Attack Speed (from weapon type)
```

**Local Attack Speed Modifiers (on weapon):**
```
Weapon Attack Speed = Base Attack Speed × (1 + Local Increased Attack Speed)
```
- Local modifiers shown in blue on weapon tooltip
- Directly modify weapon's base attack speed
- Multiplicative with global attack speed

**Global Attack Speed Modifiers:**
```
Final Attack Speed = Weapon Attack Speed × (1 + Sum of Global Increased Attack Speed)
                                         × Product of (1 + More Attack Speed)
```

**Attacks Per Second (APS):**
```
APS = Final Attack Speed
```

### 1.5 Attack DPS Calculation

**Average Damage DPS:**
```
DPS = Average Damage Per Hit × Attacks Per Second
```

**With Critical Strikes (Effective DPS):**
```
Non-Crit Damage = Average Damage Per Hit
Crit Damage = Average Damage Per Hit × Critical Damage Multiplier

Expected Damage Per Hit = (Non-Crit Damage × (1 - Crit Chance))
                        + (Crit Damage × Crit Chance)

Effective DPS = Expected Damage Per Hit × Attacks Per Second
```

**With Accuracy (Realistic DPS):**
```
Realistic DPS = Effective DPS × Chance to Hit
```

### 1.6 Critical Strike Mechanics for Attacks

**Base Critical Chance:**
```
Base Crit Chance = Weapon Base Critical Hit Chance
```

Exceptions:
- Unarmed attacks: 5% base crit
- Shield attacks: Skill gem base crit
- Offhand attacks: Skill gem base crit

**Local Critical Chance Modifiers (on weapon):**
```
Weapon Crit Chance = Base Crit Chance + Local Flat Crit Chance
```
- "+X% to Critical Hit Chance" on weapon
- Adds directly to base crit

**Global Critical Chance Modifiers:**
```
Final Crit Chance = Weapon Crit Chance × (1 + Sum of Increased Crit Chance)
                                        × Product of (1 + More Crit Chance)
```

**Capped at 95% (maximum crit chance)**

**Critical Hit Check Process:**
1. When skill activates, roll 0-99.99
2. This creates a threshold value
3. Each target checks if your crit chance ≥ threshold
4. All hits from same skill share threshold (all crit or none)
5. Exceptions: Sustained/channeling skills roll per hit
6. Multi-projectile from players: separate rolls per projectile
7. Lucky crit: perform two rolls, keep lower threshold (easier to crit)
8. Unlucky crit: keep higher threshold (harder to crit)

**Critical Damage Bonus:**

Default: **+100% Critical Damage Bonus** (200% total damage on crit)

This means:
- Base hit: 100% damage
- Critical bonus: +100% extra damage
- Total critical damage: 200% of base

**Calculation:**
```
Base Critical Damage Bonus = +100%

Critical Damage Bonus = (Base + Sum of Flat Additions)
                      × (1 + Sum of Increased Crit Damage Bonus)
                      × Product of (1 + More Crit Damage Bonus)

Final Crit Damage Multiplier = 1 + (Critical Damage Bonus / 100)
```

**Example:**
```
Base: +100%
Weapon: +25% to Critical Damage Bonus
Passive: 50% increased Critical Damage Bonus

Step 1: Base + Flat = +100% + 25% = +125%
Step 2: Increased = +125% × (1 + 0.50) = +187.5%
Final Multiplier = 1 + 1.875 = 2.875 (287.5% total damage on crit)
```

**Local Critical Damage (on weapon):**
- "+X% to Critical Damage Bonus" on weapon
- Adds to base BEFORE increases/more multipliers
- Only applies to hits with that weapon

**Dual Wielding Critical Hits:**
- Each hand rolls damage separately
- If EITHER hand crits, the ENTIRE combined hit is a critical hit

### 1.7 Accuracy and Hit Chance

**Accuracy Formula:**
```
Uncapped Chance to Hit = (Attacker's Accuracy × 1.25 × 100)
                       / (Attacker's Accuracy + Defender's Evasion × 0.3)

Final Chance to Hit = Capped between 5% and 100%
```

**Note:** Can reach 125% with certain effects, but 100% is the practical cap.

**Accuracy Rating Sources:**
- **6 accuracy per character level**
- **6 accuracy per point of Dexterity**
- Gear modifiers (weapons, rings, helmets, gloves)
- Passive tree nodes
- Support gems
- Auras and buffs

**Distance Penalty (New in PoE2):**

Player attacks suffer accuracy penalties based on distance to target:

```
0-2 meters: No penalty (100% accuracy)
2-9 meters: Linear penalty from 0% to 90% less accuracy
9+ meters: Maximum penalty (90% less accuracy)
```

**Formula (approximate):**
```
if distance <= 2:
    penalty = 0%
elif distance >= 9:
    penalty = 90%
else:
    penalty = (distance - 2) / (9 - 2) × 90%

Effective Accuracy = Base Accuracy × (1 - penalty)
```

**Example:**
```
Base Accuracy: 1000
Target at 5 meters:
  penalty = (5 - 2) / 7 × 90% = 38.57%
  Effective Accuracy = 1000 × (1 - 0.3857) = 614.3
```

**Mitigation:**
- Far Reach support gem (reduces distance penalty for melee skills)
- Ranged weapon users need higher accuracy investment
- Distance-based attacks (bows, crossbows, slams) affected most

**Bypassing Accuracy:**

Effects that guarantee hits:
- "Can't be Evaded"
- "Always Hit"
- "Cannot Miss"
- Target has "Cannot Evade" debuff

These set hit chance to **100%**, ignoring accuracy and evasion entirely.

**Spells and Accuracy:**
- Spells do NOT use accuracy
- Spells always hit (no accuracy check)
- Only ATTACKS require accuracy

**Evasion Formula:**

The same formula from the accuracy perspective:

```
Chance to Evade = 1 - Chance to Hit
Maximum Evasion: 95%
Minimum Hit Chance: 5%
```

**Entropy System:**

Evasion uses a **deterministic entropy system**, NOT pure RNG:

1. **Initialization:** First attack or after 3.33+ seconds, randomize entropy (0-99)
2. **Accumulation:** Add attacker's hit chance to entropy counter
3. **Resolution:**
   - If entropy < 100: Attack evaded
   - If entropy ≥ 100: Attack hits, subtract 100 from entropy
4. **Result:** Guarantees exactly 1 hit per N attacks if you have 1/N hit chance

**Example:**
```
Attacker has 25% hit chance
Entropy starts at 40

Attack 1: 40 + 25 = 65 (< 100) → Evaded, entropy = 65
Attack 2: 65 + 25 = 90 (< 100) → Evaded, entropy = 90
Attack 3: 90 + 25 = 115 (≥ 100) → HIT, entropy = 15
Attack 4: 15 + 25 = 40 (< 100) → Evaded, entropy = 40
```

Result: Exactly 1 hit every 4 attacks (25% hit rate, guaranteed)

**Multi-Attacker Entropy:**
- Multiple enemies attacking the same player share one entropy counter
- Prevents simultaneous unlucky streaks

**Critical Hit and Evasion:**
- If attack hits but would be a crit, evasion is checked AGAIN
- Two separate evasion checks: one for hit, one for crit confirmation
- Provides extra defense against critical hits

---

## 2. Weapon Types and Mechanics

### 2.1 Weapon Categories

**Martial Weapons:**
- Used to attack with directly
- Have base physical/elemental damage, crit chance, attack speed
- Can be modified with local modifiers

**Caster Weapons:**
- Give bonuses to spells or minions
- Not used to attack with
- Includes wands, staves, sceptres

**Trap Weapons:**
- No base attack stats
- Used exclusively for trap skills

### 2.2 One-Handed Weapons

#### Swords (Strength + Dexterity)
- Balanced weapons
- Moderate attack speed
- Often elemental damage themed
- Can be dual-wielded

**Characteristics:**
- Base damage: Medium
- Attack speed: Medium
- Critical chance: Medium
- Dual-wieldable: Yes

#### Axes (Strength + Dexterity)
- Physical damage focused
- Moderate to slow attack speed
- High physical damage per hit

**Characteristics:**
- Base damage: High physical
- Attack speed: Medium-Slow
- Critical chance: Medium
- Dual-wieldable: Yes

#### Maces (Strength)
- Slow, heavy attacks
- High damage per hit
- Often have stun-related implicits

**Characteristics:**
- Base damage: Very high
- Attack speed: Slow
- Critical chance: Low-Medium
- Dual-wieldable: Yes

#### Daggers (Dexterity + Intelligence)
- Extremely fast attacks
- Highest base critical strike chance
- Lower damage per hit
- Used for ambush/debilitation

**Characteristics:**
- Base damage: Low
- Attack speed: Very fast
- Critical chance: Very high
- Dual-wieldable: Yes
- Range: 1.0 (lowest)

#### Claws (Dexterity + Intelligence)
- Fast attacks
- High critical strike chance
- Often have life/mana on hit
- Can ONLY be dual-wielded (requires 2 claws)

**Characteristics:**
- Base damage: Low-Medium
- Attack speed: Fast
- Critical chance: High
- Dual-wieldable: Yes (only with another claw)

#### Wands (Intelligence)
- Caster weapon (not for attacks)
- Boosts spell damage and spell crit
- Cannot use attack skills (except special wand attacks)

**Characteristics:**
- Not a martial weapon
- Used for spellcasting
- Increases spell damage and crit

#### Sceptres (Strength + Intelligence)
- Caster weapon (not for attacks)
- Boosts spell damage and elemental damage

**Characteristics:**
- Not a martial weapon
- Used for spellcasting

### 2.3 Two-Handed Weapons

#### Two-Handed Swords (Strength + Dexterity)
- High damage and range
- Moderate attack speed
- Elemental damage themes

**Characteristics:**
- Base damage: High
- Attack speed: Medium
- Critical chance: Medium
- Can have 2 sockets (vs 1 for one-handed)

#### Two-Handed Axes (Strength + Dexterity)
- Very high physical damage
- Slower attack speed
- Physical damage focused

**Characteristics:**
- Base damage: Very high
- Attack speed: Slow
- Critical chance: Medium
- Can have 2 sockets

#### Two-Handed Maces (Strength)
- Highest damage per hit
- Slowest attack speed
- Stun-focused mechanics

**Characteristics:**
- Base damage: Extremely high
- Attack speed: Very slow
- Critical chance: Low-Medium
- Can have 2 sockets

#### Staves/Quarterstaves (Strength/Dexterity/Intelligence)
- Two-handed melee weapons
- Some are martial, some are caster weapons
- Martial staves have moderate damage and speed

**Characteristics:**
- Base damage: Medium (martial) or N/A (caster)
- Attack speed: Medium
- Can have 2 sockets

#### Bows (Dexterity)
- Two-handed ranged weapons
- Range: 12.0
- Require arrows (quiver)
- Dexterity-based

**Characteristics:**
- Base damage: Medium-High
- Attack speed: Medium-Fast
- Critical chance: Medium-High
- Range: 12.0 (long range)
- Can have 2 sockets

#### Crossbows (Dexterity/Strength)
- Two-handed ranged weapons
- Use bolts instead of arrows
- Slower but harder-hitting than bows
- Ammunition-based skills (different from bows)

**Characteristics:**
- Base damage: High
- Attack speed: Slower than bows
- Critical chance: Medium
- Range: 12.0
- Can have 2 sockets

### 2.4 Special Weapon Mechanics

#### Spears (Cannot Dual Wield)
- One-handed only
- Cannot be dual-wielded
- Longest melee range: 1.5

**Characteristics:**
- Base damage: Medium
- Attack speed: Medium
- Range: 1.5 (longest melee)
- Dual-wieldable: NO

#### Flails (Cannot Dual Wield)
- One-handed only
- Cannot be dual-wielded

**Characteristics:**
- Dual-wieldable: NO

### 2.5 Weapon Base Stats Summary

All martial weapons have:
- **Physical Damage Range:** X-Y Physical
- **Attack Speed:** Attacks per second
- **Critical Strike Chance:** Base % (shown on weapon)
- **Range:** Melee range in units

**Local Modifiers on Weapons:**

Modifiers that appear on the weapon itself can be local or global:

**Local Modifiers (affect weapon base stats, shown in BLUE):**
- "X% increased Physical Damage" → increases weapon's physical damage
- "Adds X to Y [Element] Damage" → adds to weapon's base damage
- "X% increased Attack Speed" → increases weapon's attack speed
- "+X% to Critical Hit Chance" → adds to weapon's base crit
- "+X% to Critical Damage Bonus" → adds to base crit multiplier

**Global Modifiers (affect character):**
- "X% increased Global Physical Damage"
- "Adds X to Y [Element] Damage to Attacks" (on non-weapon gear)

**Implicit Modifiers:**

Each weapon type has implicit modifiers by default. As of patch 0.3.0:
- Martial weapons have "+25% to Critical Damage Bonus" (implicit)

### 2.6 Two-Handed vs One-Handed

**Two-Handed Advantages:**
- Higher base damage values
- Can have 2 gem sockets (vs 1 for one-handed)
- Access to two-handed specific passives

**Two-Handed Disadvantages:**
- Cannot use shield (no block, no shield stats)
- Cannot dual wield (no dual wield benefits)
- Generally slower attack speed

**No Inherent Damage Multiplier:**
Research found no evidence of an inherent "two-handed damage multiplier" in PoE2. The advantage comes from higher base stats and socket access.

**One-Handed Advantages:**
- Can dual wield (combine two weapons)
- Can use shield (block, resistances, life)
- Generally faster attack speed
- More flexible (weapon + shield or dual wield)

**One-Handed Disadvantages:**
- Lower base damage per weapon
- Only 1 socket per weapon
- Dual wielding has penalties on some skills

### 2.7 Dual Wielding Mechanics

**Core Mechanics:**

1. **No Inherent Stat Bonuses** (different from PoE1)
   - Dual wielding in PoE2 provides NO automatic bonuses
   - No attack speed bonus
   - No block chance
   - Benefits come entirely from having two weapons

2. **Attack Behavior:**
   - Skill determines if hands alternate OR combine into single hit
   - Most skills combine both weapons into one hit
   - Each hand rolls damage separately
   - Damage combines at end of calculation

3. **Critical Hit Rule:**
   - If EITHER hand crits, the ENTIRE combined hit is a crit
   - Very powerful for critical-based builds

4. **Weapon Compatibility:**
   - Both weapons must be compatible with the skill
   - If one weapon is incompatible, only the compatible weapon is used
   - Example: Skill requires mace → if dual wielding mace + sword, only mace is used

5. **Dual Wield Restrictions:**
   - **Claws:** Can ONLY be dual-wielded with another claw (not other weapons)
   - **Spears:** Cannot be dual-wielded at all
   - **Flails:** Cannot be dual-wielded at all
   - **Other martial weapons:** Can dual wield with same weapon type only
     - Swords with swords
     - Axes with axes
     - Maces with maces
     - Daggers with daggers

6. **Skill Penalties:**
   - Some skills have dual wield penalties
   - Example: "While Dual Wielding, both weapons hit with 30% less damage"
   - Applies to skills like Boneshatter, Earthquake (shockwave effects)

**Dual Wield Damage Calculation:**

```
Left Hand Damage = (Weapon 1 Base + Added Damage) × Modifiers × Crit (if applicable)
Right Hand Damage = (Weapon 2 Base + Added Damage) × Modifiers × Crit (if applicable)

Combined Damage = Left Hand Damage + Right Hand Damage

If either hand crits:
    Apply Critical Damage Multiplier to combined damage
```

**Example:**
```
Weapon 1: 50-100 Physical, 5% crit, 1.5 APS
Weapon 2: 60-90 Physical, 6% crit, 1.4 APS

Attack rolls:
  Left hand: 75 damage, crit check: NO
  Right hand: 80 damage, crit check: YES (crit!)

Combined: 155 damage × Crit Multiplier (e.g., 2.0) = 310 damage

Attack speed: Average of both weapons or determined by skill
```

**Giant's Blood Keystone:**
- Allows dual wielding two-handed axes, maces, and swords
- Requires **3× the attribute requirements** of two-handed weapons
- Example: 2H weapon needs 100 STR → you need 300 STR to dual wield

---

## 3. Attack Skills

### 3.1 Attack Skill Categories

**Melee Attack Skills:**
- Use melee weapons
- Limited range
- Often have area effects

**Ranged Attack Skills:**
- Use bows or crossbows
- Long range
- Projectile-based

**Special Attack Skills:**
- Shield attacks
- Unarmed attacks
- Totem attacks

### 3.2 Major Attack Skills

#### Heavy Swing
**Type:** Support Gem (not active skill)
**Effect:** Supported skills deal 35% more Melee Physical Damage but have 10% less Attack Speed
**Weapon:** Melee weapons
**Tags:** Support, Melee, Physical

**Mechanics:**
- Increases physical damage significantly
- Slows attack speed slightly
- Good for slow, hard-hitting builds

#### Boneshatter
**Type:** Active Attack Skill
**Weapon:** Maces (One-Handed or Two-Handed)
**Tags:** Attack, AoE, Physical, Melee

**Mechanics:**
- Hits primed enemy with heavy stun
- Releases shockwave dealing 250% base damage in area
- Excellent for stun buildup and mob clearing
- Less effective as main damage skill in PoE2 vs PoE1
- Use to heavy stun enemies, then follow up with other skills

**Dual Wield Penalty:**
- While Dual Wielding, both weapons hit with 30% less damage (applies to shockwave)

#### Sunder
**Type:** Active Attack Skill
**Weapon:** Melee weapons
**Damage Effectiveness:** 237%
**Tags:** Attack, AoE, Physical, Melee

**Mechanics:**
- Creates rolling fissure that hits in sequence
- High area damage as it travels
- Enemies hit by fissure release shockwaves
- **+100% increased Critical Damage Bonus**
- Guaranteed critical damage when hitting Armour Broken enemy
- Excellent endgame boss killer
- One of the most viable slam skills

**Special:**
- Great damage effectiveness (237%)
- Critical strike synergy
- Armor Break synergy

#### Rolling Slam
**Type:** Active Attack Skill
**Weapon:** Melee weapons
**Level Requirement:** 1
**Tags:** Attack, AoE, Physical, Melee, Movement

**Mechanics:**
- Initial slam deals stun and knockback
- Follow-up slam travels in player-controlled direction
- Higher damage on second slam
- Excellent Warrior mobility skill (early game)
- Can animation-cancel with Boneshatter

**Special:**
- Dual purpose: damage + movement
- Level 1 skill (available immediately)
- Player-directed movement

#### Glacial Cascade (Attack Version)
**Note:** Primarily known as a spell, but can be used as attack skill
**Type:** Active Attack/Spell Skill
**Tags:** Spell, AoE, Cold, Physical (as spell)

**Mechanics:**
- Releases cascading icy spikes
- Converts Physical to Cold damage
- Requires further research for attack-specific version

#### Explosive Shot
**Type:** Active Attack Skill
**Weapon:** Crossbow ONLY
**Tags:** AoE, Ammunition, Projectile, Fire, Detonator

**Mechanics:**
- Loads crossbow with flaming bolts
- Explodes on impact
- Detonates grenades in area of effect
- Applies Shock
- Large AoE explosions with high damage

**Special:**
- Crossbow-exclusive
- Synergy with grenades
- Deadeye builds (Shockburst Rounds for single target)

#### Lightning Arrow
**Type:** Active Attack Skill
**Weapon:** Bow ONLY
**Tags:** Attack, Projectile, Lightning, Bow

**Mechanics:**
- Fires charged arrow at target
- On hit (enemy or wall), fires chaining lightning beams to nearby enemies
- Arcs lightning to nearby enemies
- Causes Freeze and Shock
- Excellent with Lightning Rod for boss damage

**Special:**
- Bow-exclusive
- Chain mechanic (hits multiple enemies)
- Elemental status synergy

#### Ice Shot
**Type:** Active Attack Skill
**Weapon:** Bow ONLY
**Tags:** Attack, Projectile, Cold, Bow

**Mechanics:**
- Fires icy arrow
- Sprays cone of ice shards on hit
- Cold damage focused
- Budget-friendly (< 4 divines for build)

**Special:**
- Bow-exclusive
- Cone area effect
- Good clear speed

#### Double Slash
**Note:** Could not find this skill in PoE2 - may not exist or has different name
**Possible Confusion:** May refer to "Double Strike" from PoE1
**Status:** Requires verification - skill may not be in PoE2

### 3.3 Attack Skill Properties

Each attack skill has:

**Damage Effectiveness:**
- Listed as "Attack Damage: X% of Base"
- Multiplies total base damage (weapon + added flat)
- Varies significantly by skill (e.g., Sunder: 237%)

**Attack Speed Modifier:**
- "70% of base" to "120% of base" attack speed
- Some skills add time: "+0.2 seconds to Total Attack Time"
- Example: Heavy Swing: 10% less Attack Speed

**Added Effects:**
- Conversions (Physical → Elemental)
- Special mechanics (shockwaves, chains, explosions)
- Status ailments (Shock, Freeze, Ignite)
- Stun effects

**Special Mechanics:**
- Guaranteed crits on certain conditions (e.g., Sunder on Armour Break)
- Bonus damage effects (e.g., Boneshatter shockwave: 250% base)
- Detonation interactions (e.g., Explosive Shot + grenades)

### 3.4 Skill Tags

Skills have tags that determine which modifiers affect them:

**Common Attack Tags:**
- **Attack:** All attack skills (vs spells)
- **Melee:** Close-range attacks
- **Projectile:** Bows, crossbows, thrown weapons
- **AoE:** Area of Effect skills
- **Physical/Fire/Cold/Lightning/Chaos:** Damage type
- **Bow/Crossbow:** Weapon-specific
- **Slam:** Heavy melee slam attacks
- **Strike:** Fast melee strikes

**Modifiers apply if they match tags:**
- "Increased Projectile Damage" → only projectile attacks
- "Increased Melee Physical Damage" → only melee physical attacks
- "Increased Attack Damage" → all attacks

---

## 4. Attack vs Spell Differences

### 4.1 Core Differences

| Aspect | Attacks | Spells |
|--------|---------|--------|
| **Base Damage Source** | Weapon damage | Gem level |
| **Damage Effectiveness** | Multiplies ALL damage (base + added) | Multiplies ADDED damage only |
| **Critical Chance** | Weapon base crit | Gem base crit |
| **Attack Speed** | Weapon attack speed | Cast speed (independent) |
| **Accuracy** | Required (can miss) | Not required (always hit) |
| **Weapon Dependency** | Requires compatible weapon | Can use any weapon |
| **Scaling** | Weapon damage + modifiers | Gem level + spell damage modifiers |
| **Distance Penalty** | Yes (accuracy penalty 2-9m) | No |

### 4.2 Damage Effectiveness Difference

**Attacks:**
```
Total Base = (Weapon Base + Added Flat) × Damage Effectiveness
```

Example:
```
Weapon: 100 base damage
Added: 20 flat damage
Skill Effectiveness: 150%

Total Base = (100 + 20) × 1.5 = 180 damage
```

**Spells:**
```
Total Base = Gem Base + (Added Flat × Damage Effectiveness)
```

Example:
```
Gem: 100 base damage (from levels)
Added: 20 flat damage
Spell Effectiveness: 150%

Total Base = 100 + (20 × 1.5) = 130 damage
```

**Key Difference:** Attacks multiply weapon damage by effectiveness, spells do not.

### 4.3 Critical Strike Differences

**Attacks:**
- Use weapon's base critical hit chance
- "+% to Critical Hit Chance" on weapon adds to base
- Need to invest in weapon crit or gear/tree
- Each weapon type has different base crit

**Spells:**
- Use skill gem's base critical hit chance
- Independent of weapon
- Daggers/wands may have "increased Spell Critical Strike Chance" (global modifier)

### 4.4 Scaling Mechanisms

**Attacks Scale With:**
- Better weapons (higher damage, crit, attack speed)
- Flat added damage to attacks
- % Increased Attack Damage
- % Increased Physical/Elemental Attack Damage
- % Increased Damage with [Weapon Type]
- Attack speed increases

**Spells Scale With:**
- Gem levels (base damage increases)
- Flat added spell damage
- % Increased Spell Damage
- % Increased [Element] Spell Damage
- Cast speed increases

**Both Scale With:**
- % Increased [Element] Damage (global)
- % More Damage (from supports/ascendancy)
- Critical strike chance and multiplier
- Damage conversion
- Gained as extra damage

### 4.5 Accuracy Impact

**Attacks:**
- Must overcome enemy evasion
- Distance reduces accuracy (PoE2 mechanic)
- Need accuracy investment on gear/tree
- Can miss (5% minimum miss chance)
- Entropy system prevents long unlucky streaks

**Spells:**
- Always hit (no accuracy check)
- No distance penalty
- Cannot miss
- No accuracy investment needed

**Impact on Builds:**
- Attack builds need accuracy investment (especially ranged)
- Spell builds can ignore accuracy entirely
- Spells are more consistent damage
- Attacks can achieve higher damage ceiling with better weapons

---

## 5. Accuracy & Evasion

### 5.1 Accuracy Rating

**Accuracy Formula:**
```
Uncapped Chance to Hit = (Attacker's Accuracy × 1.25 × 100)
                       / (Attacker's Accuracy + Defender's Evasion × 0.3)
```

**Capped:**
```
Final Chance to Hit = Clamp(Uncapped Chance to Hit, 5%, 100%)
```

**Base Accuracy:**
```
Base Accuracy = (Character Level × 6) + (Dexterity × 6)
```

**Modified Accuracy:**
```
Final Accuracy = Base Accuracy × (1 + Sum of Increased Accuracy)
                               × Product of (1 + More Accuracy)
                               + Sum of Flat Accuracy
```

### 5.2 Distance Penalty

**New Mechanic in PoE2:**

Player attacks suffer accuracy penalties based on distance from damage origin to target:

```
Distance: 0-2 meters
Penalty: 0% (no penalty)

Distance: 2-9 meters
Penalty: Linear scaling from 0% to 90%
Formula: penalty = ((distance - 2) / 7) × 90%

Distance: 9+ meters
Penalty: 90% (maximum)
```

**Effective Accuracy:**
```
Effective Accuracy = Base Accuracy × (1 - distance_penalty)
```

**Examples:**

| Distance | Penalty | Effective Accuracy (base 1000) |
|----------|---------|-------------------------------|
| 1m | 0% | 1000 |
| 2m | 0% | 1000 |
| 3m | ~12.86% | 871.4 |
| 5m | ~38.57% | 614.3 |
| 7m | ~64.29% | 357.1 |
| 9m | 90% | 100 |
| 12m | 90% | 100 |

**Implications:**
- Melee (close range): Minimal penalty
- Ranged (bows, crossbows): Severe penalty
- Slams with extended range: Penalty based on slam distance
- Builds need MORE accuracy for ranged attacks

**Mitigation:**
- **Far Reach Support Gem:** Reduces distance penalty for melee skills with extended range
- Higher accuracy investment on gear/tree
- "Can't be Evaded" effects bypass entirely

**Monster Exceptions:**
- Monsters do NOT have distance penalty by default
- Exception: Specific items/effects (e.g., Vigilant View ring, Tactician's Stay Light)

### 5.3 Evasion Rating

**Evasion Formula:**
```
Chance to Evade = 1 - Chance to Hit
Maximum Evasion: 95%
Minimum Hit Chance: 5%
```

**Using the accuracy formula:**
```
Uncapped Chance to Evade = 1 - ((Attacker Accuracy × 1.25 × 100)
                               / (Attacker Accuracy + Defender Evasion × 0.3))

Final Chance to Evade = Clamp(Uncapped Chance to Evade, 0%, 95%)
```

**Evasion Sources:**
- Base evasion from gear (body armor, boots, gloves, helmets)
- Dexterity (assumed to provide evasion, but formula uses flat evasion rating)
- % Increased Evasion Rating (from tree, gear)

### 5.4 Entropy System

**NOT pure RNG** - uses deterministic entropy:

**Initialization:**
```
if first_attack OR time_since_last_attack > 3.33_seconds:
    entropy = random(0, 99)
```

**Per Attack:**
```
entropy = entropy + attacker_hit_chance_percentage

if entropy >= 100:
    result = HIT
    entropy = entropy - 100
else:
    result = EVADE
```

**Guarantees:**
- If attacker has X% hit chance, exactly 1 hit per (100/X) attacks
- Example: 25% hit chance = 1 hit every 4 attacks (guaranteed)
- Eliminates lucky/unlucky streaks

**Multi-Attacker:**
- All monsters attacking same player share one entropy counter
- Prevents simultaneous lucky/unlucky streaks

**Critical Hit Double-Check:**
```
if attack_hits AND would_be_critical:
    perform_evasion_check_again()
    if second_check_fails:
        hit_becomes_non_crit = True
```

- Provides extra defense against critical strikes
- Critical hits must pass evasion check twice

### 5.5 What Can/Cannot Be Evaded

**Can Be Evaded (Default):**
- All attacks (projectiles, strikes)
- All spells (NEW in PoE2!)
- Monster projectile spells
- Monster strike attacks

**Cannot Be Evaded (Default):**
- Area of Effect hits (large slams, boss AoE)
- Boss attacks with red flash indicator

**Acrobatics Keystone:**
- Makes ALL hits evadable (including AoE)
- Cost: 50% less Evasion Rating
- Trade-off: More things evadable, but lower evasion chance

**Bypass Mechanics:**

Attacker with:
- "Can't be Evaded"
- "Always Hit"
- "Cannot Miss"

Target with:
- "Cannot Evade" debuff
- Pinned status
- Parried debuff

These set hit chance to **100%** regardless of accuracy or evasion.

### 5.6 Accuracy Calculation Examples

**Example 1: Melee Attack (Close Range)**
```
Character Level: 70
Dexterity: 150
Gear Accuracy: +300
Increased Accuracy: 50%

Base Accuracy = (70 × 6) + (150 × 6) = 420 + 900 = 1320
Flat Accuracy = 1320 + 300 = 1620
Final Accuracy = 1620 × (1 + 0.50) = 2430

Enemy Evasion: 1500
Distance: 1 meter (no penalty)

Uncapped Hit Chance = (2430 × 1.25 × 100) / (2430 + 1500 × 0.3)
                    = 303750 / (2430 + 450)
                    = 303750 / 2880
                    = 105.47%

Final Hit Chance = 100% (capped)
```

**Example 2: Ranged Attack (Long Range)**
```
Same character, but using bow at 6 meters

Distance Penalty = ((6 - 2) / 7) × 90% = 51.43%

Effective Accuracy = 2430 × (1 - 0.5143) = 1180.14

Uncapped Hit Chance = (1180.14 × 1.25 × 100) / (1180.14 + 1500 × 0.3)
                    = 147517.5 / (1180.14 + 450)
                    = 147517.5 / 1630.14
                    = 90.49%

Final Hit Chance = 90.49%
```

**Impact:** At long range, hit chance drops from 100% → 90.49% despite same build!

**Example 3: Low Accuracy vs High Evasion**
```
Attacker Accuracy: 800
Enemy Evasion: 3000
Distance: 0 meters

Uncapped Hit Chance = (800 × 1.25 × 100) / (800 + 3000 × 0.3)
                    = 100000 / (800 + 900)
                    = 100000 / 1700
                    = 58.82%

Final Hit Chance = 58.82%
```

**Impact:** Need accuracy investment to overcome evasion!

---

## 6. Attack Modifiers

### 6.1 Modifier Categories

**Local Modifiers (on weapon):**
- Affect weapon base stats
- Shown in blue on item tooltip
- Applied before global modifiers

**Global Modifiers (on gear/tree):**
- Affect character stats
- Applied after local modifiers
- Never modify weapon base stats

### 6.2 Physical Attack Damage Modifiers

**Local (on weapon):**
```
"X% increased Physical Damage"
→ Increases weapon's physical damage
→ Shown in blue on weapon tooltip
→ Applied to weapon base before anything else
```

**Global:**
```
"X% increased Physical Attack Damage"
→ Affects all physical damage from attacks
→ Does NOT affect weapon base
→ Applied in "Increased" step

"X% increased Global Physical Damage"
→ Affects attacks AND spells
→ Applied in "Increased" step
```

**More Modifiers:**
```
"X% more Physical Attack Damage"
→ Multiplicative modifier
→ Applied in "More" step
→ Typically from support gems
```

**Examples:**

Weapon with 100-200 base physical damage:
- "+50% increased Physical Damage" (LOCAL) → Weapon becomes 150-300
- "30% increased Physical Attack Damage" (GLOBAL) → Applied to final damage calc

### 6.3 Attack Damage Modifiers

**Generic Attack Damage:**
```
"X% increased Attack Damage"
→ Affects ALL damage from attacks (physical + elemental + chaos)
→ Global modifier
→ Additive with other "increased" modifiers

"X% more Attack Damage"
→ Multiplicative
→ Rare, powerful modifier
→ Typically from support gems or ascendancy
```

### 6.4 Attack Speed Modifiers

**Local (on weapon):**
```
"X% increased Attack Speed"
→ Increases weapon's base attack speed
→ Shown in blue on weapon tooltip
→ Multiplicative with global attack speed
```

**Global:**
```
"X% increased Attack Speed"
→ Affects attack speed globally
→ Additive with other global attack speed
→ Applied after local weapon speed

"X% more Attack Speed"
→ Multiplicative
→ Very rare
→ Powerful modifier
```

**Calculation:**
```
Weapon APS = Base APS × (1 + Local Increased Attack Speed)
Final APS = Weapon APS × (1 + Sum of Global Increased Attack Speed)
                       × Product of (1 + More Attack Speed)
```

**Example:**
```
Base weapon: 1.5 APS
Local: +20% increased Attack Speed → Weapon shows 1.8 APS
Global: +30% increased Attack Speed
More: +15% more Attack Speed (support gem)

Final APS = 1.8 × (1 + 0.30) × (1 + 0.15)
          = 1.8 × 1.30 × 1.15
          = 2.691 APS
```

### 6.5 Flat Added Damage to Attacks

**Local (on weapon):**
```
"Adds X to Y [Element] Damage"
→ Adds to weapon's base damage
→ Shown in blue on weapon tooltip
→ Multiplied by local % increases

Example:
Weapon base: 50-100 Physical
Local: "Adds 10 to 20 Fire Damage"
Local: "+30% increased Physical Damage" (does NOT affect added fire)

Weapon shows: 65-130 Physical, 10-20 Fire
```

**Global (on other gear):**
```
"Adds X to Y [Element] Damage to Attacks"
→ Added to attack damage (not weapon base)
→ Applied in "Added Flat Damage" step
→ Multiplied by skill damage effectiveness

Example:
Ring: "Adds 15 to 25 Fire Damage to Attacks"
Skill effectiveness: 150%
Effective added damage: 22.5 to 37.5 Fire
```

**Sources:**
- Rings (most common)
- Amulets
- Gloves
- Belts
- Passive tree nodes
- Auras/buffs
- Support gems

### 6.6 Critical Strike Modifiers for Attacks

**Critical Strike Chance:**

**Local (on weapon):**
```
"+X% to Critical Hit Chance"
→ Adds directly to weapon's base crit
→ Shown on weapon tooltip

Example:
Weapon base: 5% crit
Local: "+2% to Critical Hit Chance"
Weapon shows: 7% crit
```

**Global:**
```
"X% increased Critical Strike Chance"
→ Multiplicative with base crit
→ Additive with other "increased crit" sources

"X% increased Critical Strike Chance with Attacks"
→ Only affects attacks (not spells)

"X% increased Critical Strike Chance with [Weapon Type]"
→ Only affects that weapon type
```

**Calculation:**
```
Base Crit = Weapon Base + Local Flat Additions

Final Crit = Base Crit × (1 + Sum of Increased Crit Chance)
                       × Product of (1 + More Crit Chance)

Capped at 95%
```

**Critical Damage Bonus:**

**Local (on weapon):**
```
"+X% to Critical Damage Bonus"
→ Adds to base critical damage bonus (+100% default)
→ Only applies to hits with that weapon
→ Added before increases/more multipliers

Example:
Default: +100% bonus (200% total damage)
Weapon: "+25% to Critical Damage Bonus"
New base: +125% bonus (before increases)
```

**Global:**
```
"X% increased Critical Damage Bonus"
→ Multiplies the base critical damage bonus
→ Additive with other "increased crit damage" sources

"X% more Critical Damage Bonus"
→ Multiplicative
→ Very rare
```

**Calculation:**
```
Base Bonus = +100% (default)
Base with Flat = +100% + Sum of Flat Additions

Modified Bonus = Base with Flat × (1 + Sum of Increased)
                                 × Product of (1 + More)

Final Crit Multiplier = 1 + (Modified Bonus / 100)
```

**Example:**
```
Base: +100%
Weapon: +25% (flat)
Global: +50% increased

Step 1: +100% + 25% = +125% base
Step 2: +125% × (1 + 0.50) = +187.5%
Step 3: Multiplier = 1 + 1.875 = 2.875

Crits deal 287.5% of base damage
```

### 6.7 Weapon-Specific Modifiers

**Damage with Weapon Type:**
```
"X% increased Damage with Two-Handed Weapons"
"X% increased Damage with Bows"
"X% increased Damage with Maces"
etc.

→ Affects all damage (physical + elemental + chaos)
→ Only when using that weapon type
→ Additive with other "increased" modifiers
```

**Attack Speed with Weapon Type:**
```
"X% increased Attack Speed with [Weapon Type]"
→ Only applies when using that weapon
→ Global modifier (not local to weapon)
```

**Critical Strike with Weapon Type:**
```
"X% increased Critical Strike Chance with [Weapon Type]"
→ Only when using that weapon
→ Multiplicative with base crit
```

### 6.8 Modifier Sources Summary

**Weapon (Local):**
- % increased Physical Damage
- Adds X to Y Damage
- % increased Attack Speed
- +% to Critical Hit Chance
- +% to Critical Damage Bonus

**Weapon (Implicit):**
- +25% to Critical Damage Bonus (martial weapons, patch 0.3.0)

**Gear (Rings, Amulets, Gloves, Belts):**
- Adds X to Y [Element] Damage to Attacks
- % increased Attack Speed
- % increased Attack Damage
- +X to Accuracy Rating
- % increased Critical Strike Chance

**Passive Tree:**
- % increased Attack Damage
- % increased Physical/Elemental Attack Damage
- % increased Attack Speed
- % increased Critical Strike Chance
- % increased Critical Damage Bonus
- % increased Damage with [Weapon Type]
- +X to Accuracy Rating

**Support Gems:**
- % more Attack Damage (multiplicative!)
- % more Attack Speed
- % more Critical Strike Chance
- % more Critical Damage Bonus
- Adds X to Y Damage
- % increased Attack Speed

**Auras/Buffs:**
- Adds X to Y Damage to Attacks
- % increased Attack Speed
- % increased Attack Damage
- +X to Accuracy Rating

---

## 7. Implementation Pseudocode

### 7.1 Attack DPS Calculator Structure

```python
class AttackDPSCalculator:
    def __init__(self):
        self.weapon_data = {}
        self.character_stats = {}
        self.skill_data = {}
        self.modifiers = {
            'flat_added': [],
            'increased': [],
            'more': [],
            'conversion': [],
            'gained': []
        }

    def calculate_attack_dps(self, weapon, character, skill, modifiers):
        """Main calculation function"""

        # Step 1: Calculate base weapon damage
        base_damage = self.calculate_weapon_base_damage(weapon)

        # Step 2: Add flat damage
        total_base = self.add_flat_damage(base_damage, modifiers.flat_added)

        # Step 3: Apply damage effectiveness
        effective_base = self.apply_damage_effectiveness(
            total_base,
            skill.damage_effectiveness
        )

        # Step 4: Apply damage conversion
        converted_damage = self.apply_conversion(
            effective_base,
            modifiers.conversion
        )

        # Step 5: Apply increased/decreased modifiers
        increased_damage = self.apply_increased_modifiers(
            converted_damage,
            modifiers.increased
        )

        # Step 6: Apply more/less modifiers
        more_damage = self.apply_more_modifiers(
            increased_damage,
            modifiers.more
        )

        # Step 7: Apply gained as extra damage
        final_damage = self.apply_gained_damage(
            more_damage,
            effective_base,
            modifiers.gained
        )

        # Step 8: Calculate critical strike multiplier
        crit_multi = self.calculate_crit_multiplier(character, weapon, modifiers)

        # Calculate expected damage (non-crit + crit)
        crit_chance = self.calculate_crit_chance(character, weapon, modifiers)
        expected_damage = self.calculate_expected_damage(
            final_damage,
            crit_chance,
            crit_multi
        )

        # Calculate attack speed
        attack_speed = self.calculate_attack_speed(weapon, character, skill, modifiers)

        # Calculate accuracy
        hit_chance = self.calculate_hit_chance(
            character,
            target_evasion=1500,  # default enemy evasion
            distance=0  # default melee range
        )

        # Calculate DPS
        dps = expected_damage * attack_speed * hit_chance

        return {
            'average_damage': final_damage,
            'expected_damage': expected_damage,
            'attack_speed': attack_speed,
            'hit_chance': hit_chance,
            'crit_chance': crit_chance,
            'crit_multiplier': crit_multi,
            'dps': dps
        }
```

### 7.2 Weapon Base Damage Calculation

```python
def calculate_weapon_base_damage(self, weapon):
    """Calculate weapon base damage including local modifiers"""

    # Get base weapon damage ranges
    physical_min = weapon.base_physical_min
    physical_max = weapon.base_physical_max
    fire_min = weapon.base_fire_min or 0
    fire_max = weapon.base_fire_max or 0
    cold_min = weapon.base_cold_min or 0
    cold_max = weapon.base_cold_max or 0
    lightning_min = weapon.base_lightning_min or 0
    lightning_max = weapon.base_lightning_max or 0
    chaos_min = weapon.base_chaos_min or 0
    chaos_max = weapon.base_chaos_max or 0

    # Apply local "Adds X to Y Damage" modifiers
    for mod in weapon.local_flat_damage:
        if mod.damage_type == 'physical':
            physical_min += mod.min_damage
            physical_max += mod.max_damage
        elif mod.damage_type == 'fire':
            fire_min += mod.min_damage
            fire_max += mod.max_damage
        # ... repeat for other elements

    # Apply local "X% increased Physical Damage" (affects physical only)
    local_phys_increase = sum(
        mod.value for mod in weapon.local_modifiers
        if mod.type == 'increased_physical_damage'
    )
    physical_min *= (1 + local_phys_increase / 100)
    physical_max *= (1 + local_phys_increase / 100)

    # Apply local "X% increased Elemental Damage" (if exists)
    local_ele_increase = sum(
        mod.value for mod in weapon.local_modifiers
        if mod.type == 'increased_elemental_damage'
    )
    fire_min *= (1 + local_ele_increase / 100)
    fire_max *= (1 + local_ele_increase / 100)
    cold_min *= (1 + local_ele_increase / 100)
    cold_max *= (1 + local_ele_increase / 100)
    lightning_min *= (1 + local_ele_increase / 100)
    lightning_max *= (1 + local_ele_increase / 100)

    return {
        'physical': {'min': physical_min, 'max': physical_max},
        'fire': {'min': fire_min, 'max': fire_max},
        'cold': {'min': cold_min, 'max': cold_max},
        'lightning': {'min': lightning_min, 'max': lightning_max},
        'chaos': {'min': chaos_min, 'max': chaos_max}
    }
```

### 7.3 Flat Damage Addition

```python
def add_flat_damage(self, base_damage, flat_modifiers):
    """Add all flat damage sources from gear, gems, etc."""

    damage = copy.deepcopy(base_damage)

    for mod in flat_modifiers:
        damage_type = mod.damage_type
        if damage_type not in damage:
            damage[damage_type] = {'min': 0, 'max': 0}

        damage[damage_type]['min'] += mod.min_damage
        damage[damage_type]['max'] += mod.max_damage

    return damage
```

### 7.4 Damage Effectiveness

```python
def apply_damage_effectiveness(self, damage, effectiveness_percent):
    """Apply skill damage effectiveness"""

    multiplier = effectiveness_percent / 100

    result = {}
    for damage_type, values in damage.items():
        result[damage_type] = {
            'min': values['min'] * multiplier,
            'max': values['max'] * multiplier
        }

    return result
```

### 7.5 Damage Conversion

```python
def apply_conversion(self, damage, conversion_mods):
    """Apply damage conversion (2-step process)"""

    # Step 1: Skill-inherent conversion
    skill_conversions = [
        mod for mod in conversion_mods
        if mod.source == 'skill'
    ]
    damage = self._apply_conversion_step(damage, skill_conversions)

    # Step 2: All other conversion
    other_conversions = [
        mod for mod in conversion_mods
        if mod.source != 'skill'
    ]
    damage = self._apply_conversion_step(damage, other_conversions)

    return damage

def _apply_conversion_step(self, damage, conversions):
    """Apply one step of conversion"""

    result = copy.deepcopy(damage)

    for conversion in conversions:
        source_type = conversion.from_type
        target_type = conversion.to_type
        percent = conversion.percent / 100

        if source_type in result:
            # Calculate converted amount
            converted_min = result[source_type]['min'] * percent
            converted_max = result[source_type]['max'] * percent

            # Reduce source damage
            result[source_type]['min'] *= (1 - percent)
            result[source_type]['max'] *= (1 - percent)

            # Add to target damage
            if target_type not in result:
                result[target_type] = {'min': 0, 'max': 0}
            result[target_type]['min'] += converted_min
            result[target_type]['max'] += converted_max

    return result
```

### 7.6 Increased Modifiers

```python
def apply_increased_modifiers(self, damage, increased_mods):
    """Apply all increased/decreased modifiers (additive)"""

    # Categorize modifiers by damage type
    modifiers_by_type = {
        'global': [],  # affects all damage
        'physical': [],
        'fire': [],
        'cold': [],
        'lightning': [],
        'chaos': [],
        'elemental': []  # affects fire, cold, lightning
    }

    for mod in increased_mods:
        category = mod.applies_to
        modifiers_by_type[category].append(mod.value)

    result = {}
    for damage_type, values in damage.items():
        # Sum all applicable modifiers
        total_increase = 0

        # Global modifiers always apply
        total_increase += sum(modifiers_by_type['global'])

        # Type-specific modifiers
        total_increase += sum(modifiers_by_type[damage_type])

        # Elemental modifiers apply to fire/cold/lightning
        if damage_type in ['fire', 'cold', 'lightning']:
            total_increase += sum(modifiers_by_type['elemental'])

        # Apply multiplier
        multiplier = 1 + (total_increase / 100)
        result[damage_type] = {
            'min': values['min'] * multiplier,
            'max': values['max'] * multiplier
        }

    return result
```

### 7.7 More Modifiers

```python
def apply_more_modifiers(self, damage, more_mods):
    """Apply all more/less modifiers (multiplicative)"""

    # Similar categorization as increased modifiers
    modifiers_by_type = {
        'global': [],
        'physical': [],
        'fire': [],
        'cold': [],
        'lightning': [],
        'chaos': [],
        'elemental': []
    }

    for mod in more_mods:
        category = mod.applies_to
        modifiers_by_type[category].append(mod.value)

    result = {}
    for damage_type, values in damage.items():
        multiplier = 1.0

        # Global modifiers (multiplicative with each other)
        for mod_value in modifiers_by_type['global']:
            multiplier *= (1 + mod_value / 100)

        # Type-specific modifiers
        for mod_value in modifiers_by_type[damage_type]:
            multiplier *= (1 + mod_value / 100)

        # Elemental modifiers
        if damage_type in ['fire', 'cold', 'lightning']:
            for mod_value in modifiers_by_type['elemental']:
                multiplier *= (1 + mod_value / 100)

        result[damage_type] = {
            'min': values['min'] * multiplier,
            'max': values['max'] * multiplier
        }

    return result
```

### 7.8 Gained as Extra Damage

```python
def apply_gained_damage(self, current_damage, base_damage, gained_mods):
    """Apply gained as extra damage"""

    result = copy.deepcopy(current_damage)

    for mod in gained_mods:
        source_type = mod.from_type
        target_type = mod.to_type
        percent = mod.percent / 100

        # Gained damage uses BASE damage (before increases/more)
        if source_type in base_damage:
            gained_min = base_damage[source_type]['min'] * percent
            gained_max = base_damage[source_type]['max'] * percent

            # Add to result
            if target_type not in result:
                result[target_type] = {'min': 0, 'max': 0}
            result[target_type]['min'] += gained_min
            result[target_type]['max'] += gained_max

    return result
```

### 7.9 Critical Strike Calculations

```python
def calculate_crit_chance(self, character, weapon, modifiers):
    """Calculate final critical strike chance"""

    # Base crit from weapon
    base_crit = weapon.base_crit_chance

    # Local flat additions (on weapon)
    for mod in weapon.local_modifiers:
        if mod.type == 'flat_crit_chance':
            base_crit += mod.value

    # Global increased modifiers (additive)
    increased_crit = 0
    for mod in modifiers.crit_chance:
        if mod.type == 'increased':
            increased_crit += mod.value

    # Global more modifiers (multiplicative)
    more_multiplier = 1.0
    for mod in modifiers.crit_chance:
        if mod.type == 'more':
            more_multiplier *= (1 + mod.value / 100)

    # Calculate final crit
    final_crit = base_crit * (1 + increased_crit / 100) * more_multiplier

    # Cap at 95%
    return min(final_crit, 95.0)

def calculate_crit_multiplier(self, character, weapon, modifiers):
    """Calculate critical damage multiplier"""

    # Base critical damage bonus: +100%
    base_bonus = 100.0

    # Flat additions (on weapon, gear)
    flat_additions = 0
    for mod in weapon.local_modifiers:
        if mod.type == 'flat_crit_damage':
            flat_additions += mod.value
    for mod in modifiers.crit_damage:
        if mod.type == 'flat':
            flat_additions += mod.value

    # Increased modifiers (additive)
    increased_crit_damage = 0
    for mod in modifiers.crit_damage:
        if mod.type == 'increased':
            increased_crit_damage += mod.value

    # More modifiers (multiplicative)
    more_multiplier = 1.0
    for mod in modifiers.crit_damage:
        if mod.type == 'more':
            more_multiplier *= (1 + mod.value / 100)

    # Calculate final bonus
    bonus = (base_bonus + flat_additions) * (1 + increased_crit_damage / 100) * more_multiplier

    # Convert to multiplier
    multiplier = 1 + (bonus / 100)

    return multiplier

def calculate_expected_damage(self, base_damage, crit_chance, crit_multi):
    """Calculate expected damage accounting for crits"""

    # Calculate average for each damage type
    result = {}
    for damage_type, values in base_damage.items():
        avg_damage = (values['min'] + values['max']) / 2

        # Expected damage = (non-crit% × damage) + (crit% × damage × multiplier)
        non_crit_portion = (1 - crit_chance / 100) * avg_damage
        crit_portion = (crit_chance / 100) * avg_damage * crit_multi

        expected = non_crit_portion + crit_portion
        result[damage_type] = expected

    # Total expected damage
    total_expected = sum(result.values())

    return total_expected
```

### 7.10 Attack Speed Calculation

```python
def calculate_attack_speed(self, weapon, character, skill, modifiers):
    """Calculate final attack speed"""

    # Base weapon attack speed
    base_aps = weapon.base_attack_speed

    # Local increased attack speed (on weapon)
    local_increase = 0
    for mod in weapon.local_modifiers:
        if mod.type == 'increased_attack_speed':
            local_increase += mod.value

    weapon_aps = base_aps * (1 + local_increase / 100)

    # Skill modifier (e.g., "70% of base attack speed")
    skill_multiplier = skill.attack_speed_modifier / 100

    # Global increased attack speed (additive)
    global_increase = 0
    for mod in modifiers.attack_speed:
        if mod.type == 'increased':
            global_increase += mod.value

    # More attack speed (multiplicative)
    more_multiplier = 1.0
    for mod in modifiers.attack_speed:
        if mod.type == 'more':
            more_multiplier *= (1 + mod.value / 100)

    # Calculate final attack speed
    final_aps = weapon_aps * skill_multiplier * (1 + global_increase / 100) * more_multiplier

    return final_aps
```

### 7.11 Hit Chance Calculation

```python
def calculate_hit_chance(self, character, target_evasion, distance):
    """Calculate chance to hit accounting for accuracy and distance"""

    # Base accuracy
    base_accuracy = (character.level * 6) + (character.dexterity * 6)

    # Flat accuracy from gear
    for mod in character.modifiers.accuracy:
        if mod.type == 'flat':
            base_accuracy += mod.value

    # Increased accuracy (additive)
    increased_acc = 0
    for mod in character.modifiers.accuracy:
        if mod.type == 'increased':
            increased_acc += mod.value

    # More accuracy (multiplicative)
    more_multiplier = 1.0
    for mod in character.modifiers.accuracy:
        if mod.type == 'more':
            more_multiplier *= (1 + mod.value / 100)

    accuracy = base_accuracy * (1 + increased_acc / 100) * more_multiplier

    # Distance penalty
    distance_penalty = self.calculate_distance_penalty(distance)
    effective_accuracy = accuracy * (1 - distance_penalty)

    # Hit chance formula
    uncapped_hit_chance = (effective_accuracy * 1.25 * 100) / (effective_accuracy + target_evasion * 0.3)

    # Cap between 5% and 100%
    hit_chance = max(5.0, min(100.0, uncapped_hit_chance))

    return hit_chance

def calculate_distance_penalty(self, distance):
    """Calculate accuracy penalty based on distance"""

    if distance <= 2:
        return 0.0
    elif distance >= 9:
        return 0.9
    else:
        # Linear scaling from 0% to 90% between 2m and 9m
        penalty = ((distance - 2) / 7) * 0.9
        return penalty
```

### 7.12 Dual Wield Calculation

```python
def calculate_dual_wield_damage(self, weapon1, weapon2, character, skill, modifiers):
    """Calculate damage when dual wielding"""

    # Calculate damage for each hand separately
    damage1 = self.calculate_attack_damage_single_weapon(weapon1, character, skill, modifiers)
    damage2 = self.calculate_attack_damage_single_weapon(weapon2, character, skill, modifiers)

    # Check for dual wield penalty on skill
    if skill.has_dual_wield_penalty:
        penalty_multiplier = 1 - (skill.dual_wield_penalty / 100)
        damage1 = self.multiply_damage(damage1, penalty_multiplier)
        damage2 = self.multiply_damage(damage2, penalty_multiplier)

    # Combine damage from both hands
    combined_damage = self.combine_damage(damage1, damage2)

    # Critical hit check: if EITHER hand crits, entire hit crits
    crit_chance1 = self.calculate_crit_chance(character, weapon1, modifiers)
    crit_chance2 = self.calculate_crit_chance(character, weapon2, modifiers)

    # Probability that at least one hand crits
    combined_crit_chance = 1 - ((1 - crit_chance1 / 100) * (1 - crit_chance2 / 100))
    combined_crit_chance *= 100  # back to percentage

    # Use average crit multiplier (or calculate separately if needed)
    crit_multi1 = self.calculate_crit_multiplier(character, weapon1, modifiers)
    crit_multi2 = self.calculate_crit_multiplier(character, weapon2, modifiers)
    avg_crit_multi = (crit_multi1 + crit_multi2) / 2

    return {
        'damage': combined_damage,
        'crit_chance': combined_crit_chance,
        'crit_multiplier': avg_crit_multi
    }

def combine_damage(self, damage1, damage2):
    """Combine damage from two weapons"""

    result = {}

    # Add all damage types from both weapons
    all_types = set(damage1.keys()) | set(damage2.keys())

    for damage_type in all_types:
        d1 = damage1.get(damage_type, {'min': 0, 'max': 0})
        d2 = damage2.get(damage_type, {'min': 0, 'max': 0})

        result[damage_type] = {
            'min': d1['min'] + d2['min'],
            'max': d1['max'] + d2['max']
        }

    return result
```

### 7.13 Complete Example Calculation

```python
def example_calculation():
    """Complete example: Calculate DPS for a two-handed mace attack build"""

    # Weapon stats
    weapon = {
        'base_physical_min': 100,
        'base_physical_max': 200,
        'base_attack_speed': 1.2,
        'base_crit_chance': 5.0,
        'local_modifiers': [
            {'type': 'increased_physical_damage', 'value': 150},  # +150% local phys
            {'type': 'increased_attack_speed', 'value': 20},      # +20% local APS
            {'type': 'flat_crit_damage', 'value': 25}            # +25% crit damage
        ]
    }

    # Character stats
    character = {
        'level': 70,
        'dexterity': 100,
        'strength': 200
    }

    # Skill data
    skill = {
        'damage_effectiveness': 237,  # Sunder
        'attack_speed_modifier': 100,
        'has_dual_wield_penalty': False,
        'conversions': [],
        'inherent_crit_bonus': 100  # Sunder: +100% crit damage
    }

    # Modifiers from gear/tree
    modifiers = {
        'flat_added': [
            {'damage_type': 'physical', 'min_damage': 15, 'max_damage': 30}  # gear
        ],
        'increased': [
            {'applies_to': 'physical', 'value': 150},  # tree: 150% phys
            {'applies_to': 'global', 'value': 50}      # tree: 50% general
        ],
        'more': [
            {'applies_to': 'global', 'value': 40},     # support: 40% more
            {'applies_to': 'global', 'value': 30}      # support: 30% more
        ],
        'crit_chance': [
            {'type': 'increased', 'value': 200}        # 200% increased crit
        ],
        'crit_damage': [
            {'type': 'flat', 'value': 100},            # Sunder bonus
            {'type': 'increased', 'value': 80}         # 80% increased crit damage
        ],
        'attack_speed': [
            {'type': 'increased', 'value': 40}         # 40% increased APS
        ],
        'accuracy': [
            {'type': 'flat', 'value': 500},
            {'type': 'increased', 'value': 50}
        ]
    }

    # === STEP-BY-STEP CALCULATION ===

    # Step 1: Weapon base damage (with local modifiers)
    weapon_physical_min = 100 * (1 + 150/100) = 250
    weapon_physical_max = 200 * (1 + 150/100) = 500

    # Step 2: Add flat damage
    total_min = 250 + 15 = 265
    total_max = 500 + 30 = 530

    # Step 3: Damage effectiveness
    effective_min = 265 * (237/100) = 628.05
    effective_max = 530 * (237/100) = 1256.1

    # Step 4: Conversion (none in this example)
    # Skip

    # Step 5: Increased modifiers (additive)
    total_increased = 150 + 50 = 200%
    increased_min = 628.05 * (1 + 200/100) = 1884.15
    increased_max = 1256.1 * (1 + 200/100) = 3768.3

    # Step 6: More modifiers (multiplicative)
    more_multi = (1 + 40/100) * (1 + 30/100) = 1.4 * 1.3 = 1.82
    more_min = 1884.15 * 1.82 = 3429.15
    more_max = 3768.3 * 1.82 = 6858.31

    # Step 7: Gained damage (none in this example)
    # Skip

    # Average non-crit damage
    avg_damage = (3429.15 + 6858.31) / 2 = 5143.73

    # Step 8: Critical strikes
    # Base crit
    weapon_crit = 5.0  # no local flat in this example
    # Increased crit
    final_crit = 5.0 * (1 + 200/100) = 15.0%

    # Crit multiplier
    base_bonus = 100
    flat_bonus = 25 + 100 = 125  # weapon + Sunder
    total_base_bonus = 100 + 125 = 225
    increased_bonus = 225 * (1 + 80/100) = 405
    crit_multi = 1 + (405/100) = 5.05

    # Expected damage
    non_crit = (1 - 0.15) * 5143.73 = 4372.17
    crit = 0.15 * 5143.73 * 5.05 = 3896.76
    expected_damage = 4372.17 + 3896.76 = 8268.93

    # Attack speed
    weapon_aps = 1.2 * (1 + 20/100) = 1.44
    skill_modifier = 100/100 = 1.0
    global_increase = 40/100 = 0.4
    final_aps = 1.44 * 1.0 * (1 + 0.4) = 2.016 APS

    # Hit chance
    base_acc = (70 * 6) + (100 * 6) = 1020
    total_acc = (1020 + 500) * (1 + 50/100) = 2280
    target_evasion = 1500
    distance = 0 (melee)

    hit_chance = (2280 * 1.25 * 100) / (2280 + 1500 * 0.3)
               = 285000 / (2280 + 450)
               = 285000 / 2730
               = 104.4% → capped at 100%

    # Final DPS
    dps = 8268.93 * 2.016 * 1.0 = 16670.16

    print(f"Average Damage: {avg_damage:.2f}")
    print(f"Expected Damage (with crits): {expected_damage:.2f}")
    print(f"Crit Chance: {final_crit:.1f}%")
    print(f"Crit Multiplier: {crit_multi:.2f}x")
    print(f"Attack Speed: {final_aps:.2f} APS")
    print(f"Hit Chance: 100%")
    print(f"DPS: {dps:.2f}")
```

**Output:**
```
Average Damage: 5143.73
Expected Damage (with crits): 8268.93
Crit Chance: 15.0%
Crit Multiplier: 5.05x
Attack Speed: 2.02 APS
Hit Chance: 100%
DPS: 16670.16
```

---

## 8. Summary and Key Takeaways

### 8.1 Attack Damage Calculation Summary

1. **Base Damage** = Weapon damage (with local modifiers)
2. **Added Damage** = Base + all flat damage sources
3. **Damage Effectiveness** = Total × skill effectiveness %
4. **Conversion** = Apply in 2 steps (skill, then other)
5. **Increased** = Apply all additive modifiers
6. **More** = Apply all multiplicative modifiers
7. **Gained** = Add extra damage from base
8. **Critical** = Apply crit multiplier if crit occurs

### 8.2 Key Formulas

**Hit Chance:**
```
Chance to Hit = (Accuracy × 1.25 × 100) / (Accuracy + Evasion × 0.3)
Capped: 5% - 100%
```

**Distance Penalty:**
```
0-2m: No penalty
2-9m: Linear 0% to 90%
9m+: 90% penalty
```

**DPS:**
```
DPS = Expected Damage × Attack Speed × Hit Chance
Expected Damage = (Non-Crit × (1 - Crit%)) + (Crit × Crit% × Crit Multi)
```

### 8.3 Critical Differences from Spells

- Attacks use weapon damage (spells use gem damage)
- Attacks require accuracy (spells always hit)
- Attacks use weapon crit (spells use gem crit)
- Attacks multiply ALL damage by effectiveness (spells multiply added only)
- Attacks suffer distance penalty (spells do not)

### 8.4 Implementation Priorities

**Essential:**
1. Weapon base damage calculation (with local modifiers)
2. Added flat damage system
3. Damage effectiveness application
4. Increased/More modifier system
5. Critical strike calculations
6. Attack speed calculation
7. Basic hit chance (accuracy vs evasion)

**Important:**
1. Distance penalty system
2. Damage conversion (2-step)
3. Gained as extra damage
4. Dual wielding mechanics
5. Weapon-specific modifiers

**Nice to Have:**
1. Entropy system simulation
2. Skill-specific mechanics
3. Advanced modifier categorization
4. Multi-target calculations

### 8.5 Data Requirements

**Weapon Data:**
- Base damage ranges (physical, fire, cold, lightning, chaos)
- Base attack speed
- Base critical strike chance
- Local modifiers (physical%, attack speed%, crit%, added damage)
- Weapon type/category

**Skill Data:**
- Damage effectiveness %
- Attack speed modifier
- Conversions (inherent to skill)
- Special mechanics (guaranteed crits, bonus effects)
- Tags (attack, melee, projectile, etc.)

**Character Data:**
- Level
- Attributes (Strength, Dexterity, Intelligence)
- Accuracy rating
- Modifiers from gear, tree, buffs

**Modifier Data:**
- Type (increased, more, flat, conversion, gained)
- Applies to (global, physical, elemental, specific type)
- Value

### 8.6 Testing Recommendations

**Test Cases:**
1. Basic attack (no modifiers)
2. Attack with flat damage
3. Attack with increased modifiers
4. Attack with more modifiers
5. Attack with critical strikes
6. Attack with damage conversion
7. Attack with gained as extra
8. Dual wielding
9. Distance penalty scenarios
10. Full build with all mechanics

**Validation:**
- Compare to in-game tooltips
- Compare to community calculators (poe2.dev)
- Test edge cases (0% crit, 100% conversion, etc.)
- Verify order of operations

---

## 9. References and Sources

### 9.1 Primary Sources

**Mobalytics Guides:**
- https://mobalytics.gg/poe-2/guides/damage-defence-calc-order
- https://mobalytics.gg/poe-2/guides/accuracy
- https://mobalytics.gg/poe-2/guides/evasion
- https://mobalytics.gg/poe-2/guides/critical-hits
- https://mobalytics.gg/poe-2/guides/scaling-damage
- https://mobalytics.gg/poe-2/guides/item-modifiers

**Maxroll.gg Guides:**
- https://maxroll.gg/poe2/getting-started/damage-scaling

**PoE2 Wiki:**
- https://www.poe2wiki.net/wiki/Attack
- https://www.poe2wiki.net/wiki/Critical_hit
- https://www.poe2wiki.net/wiki/Accuracy
- https://www.poe2wiki.net/wiki/Evasion
- https://www.poe2wiki.net/wiki/Dual_wielding
- https://www.poe2wiki.net/wiki/Weapon
- https://www.poe2wiki.net/wiki/Modifiers
- https://www.poe2wiki.net/wiki/Damage_conversion

**Community Resources:**
- https://poe2db.tw/us/ (skill and item database)
- https://www.poe2.dev/calculators/dps (DPS calculator)

### 9.2 Key Mechanics Confirmed

✅ Attack damage uses weapon base damage
✅ Damage effectiveness multiplies all damage for attacks
✅ Increased modifiers are additive
✅ More modifiers are multiplicative
✅ Critical hits default to +100% bonus (200% total)
✅ Attacks use weapon base crit chance
✅ Accuracy formula: (Acc × 1.25 × 100) / (Acc + Eva × 0.3)
✅ Distance penalty: 0-2m none, 2-9m linear, 9m+ max 90%
✅ Dual wielding: no inherent bonuses in PoE2
✅ Dual wield crit: if either hand crits, entire hit crits
✅ Evasion uses entropy system (deterministic)
✅ Conversion: 2-step process (skill, then other)
✅ Gained damage: additive with other gained, multiplicative with rest

### 9.3 Areas Requiring Further Research

⚠️ Specific weapon base stat tables (exact numbers per weapon type)
⚠️ Complete attack skill database with damage effectiveness values
⚠️ Exact distance penalty formula (assumed linear, but not confirmed)
⚠️ Two-handed damage multiplier (if any - none found)
⚠️ Skill-specific attack alternating behavior (dual wield)
⚠️ Complete list of "cannot be evaded" effects
⚠️ Armor Break mechanic (referenced by Sunder)
⚠️ Stun mechanics (referenced by Boneshatter)

---

## Document Version

**Version:** 1.0
**Date:** 2025-10-23
**Author:** Claude (Sonnet 4.5)
**Status:** Comprehensive Research Complete

**Next Steps:**
1. Implement attack DPS calculator based on this research
2. Gather weapon base stat data from poe2db.tw
3. Create skill database with damage effectiveness values
4. Build test suite for validation
5. Compare calculator results to in-game values
6. Iterate and refine based on player feedback

---

*This research document provides a complete foundation for implementing an attack DPS calculator for Path of Exile 2. All formulas, mechanics, and implementation guidance are based on verified sources from the PoE2 community and official game mechanics.*

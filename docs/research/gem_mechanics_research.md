# Path of Exile Gem and Skill Mechanics - Comprehensive Research

## Table of Contents
1. [Gem Experience and Leveling](#gem-experience-and-leveling)
2. [Gem Level Scaling](#gem-level-scaling)
3. [Quality Mechanics](#quality-mechanics)
4. [Support Gem Mana Multipliers](#support-gem-mana-multipliers)
5. [Damage Calculation Formulas](#damage-calculation-formulas)
6. [Support Gem Effectiveness](#support-gem-effectiveness)
7. [Gem Tags and Interactions](#gem-tags-and-interactions)
8. [Specific Gem Examples](#specific-gem-examples)
9. [Advanced Mechanics](#advanced-mechanics)

---

## Gem Experience and Leveling

### Experience Gain Formula
```
Gem Experience = Character Experience × 0.10 (before level penalties)
```

**Key Points:**
- Gems gain 10% of the experience your character earns, calculated BEFORE any level penalties
- Gems retain experience when traded
- Gems do NOT lose experience upon character death
- Items with "+X% experience" modifiers affect gem leveling rates
- Gems in inactive weapon slots still accumulate experience

### Level Caps and Requirements
- **Standard cap:** Level 20 for most gems
- **Maximum achievable level:** 32 (through combined methods)
- **Level increase methods:**
  - Item modifiers granting +skill gem levels
  - Corruptions increasing gem levels
  - Linked support gems (Empower, Awakened Gems)

**Important Note:** Attribute and level requirements do NOT increase when using item modifiers or support gems, EXCEPT when corrupting the gem itself.

### Empower Support Example (Experience Requirements)
| Gem Level | Required Level | Required Strength | Gem Level Boost | Experience Required |
|-----------|---------------|-------------------|-----------------|---------------------|
| 1 | 1 | 0 | No effect | 0 |
| 2 | 10 | 21 | +1 | 226,854,909 |
| 3 | 45 | 73 | +2 | 1,439,190,228 |

---

## Gem Level Scaling

### General Level Scaling Patterns

**Skill Gems typically scale:**
- Base damage (varies widely by skill)
- Mana cost (increases with level)
- Attribute requirements (Str/Dex/Int)
- Effect magnitudes (AoE, duration, etc.)

**Support Gems typically scale:**
- Effect magnitude (damage %, speed %, etc.)
- Attribute requirements
- Generally maintain constant mana multiplier across all levels

### Attribute Requirement Scaling Examples

**Intelligence-based gems (e.g., Increased Critical Strikes Support):**
| Level | Required Level | Required Intelligence |
|-------|---------------|-----------------------|
| 1 | 8 | 18 |
| 5 | 21 | 37 |
| 10 | 40 | 66 |
| 15 | 55 | 88 |
| 20 | 70 | 111 |

**Pattern:** Intelligence requirements scale approximately linearly, increasing by 4-5 points per gem level.

---

## Quality Mechanics

### Quality Scaling Formula
```
Effective Bonus = floor(Base Quality Effect × Quality Percentage)
```

**Important:** Quality effects are ALWAYS rounded DOWN to whole numbers.

**Example:**
- Gem with 0.5% base effect per quality
- At 3% quality: floor(0.5% × 3) = floor(1.5%) = 1%

### Quality Caps
- **Standard cap:** 20% quality
- **Can exceed 20% through:**
  - Corruption
  - Specific crafting methods
  - Certain gear modifiers

### Quality Improvement Methods
1. **Currency orbs:** Add 1% quality per use
2. **Vendor recipe:** Sell level 20 gem + GCP = level 1 gem with 20% quality
3. **Corruption:** Can increase quality above 20% (risky, may brick gem)

### Alternate Quality Types
- **Anomalous:** Alternate quality effect
- **Divergent:** Alternate quality effect
- **Phantasmal:** Alternate quality effect

**Source:** Can be found in Grand Heists

**Note:** Specific quality bonuses vary by gem and must be checked individually.

---

## Support Gem Mana Multipliers

### How Mana Multipliers Stack
```
Final Mana Cost = Base Skill Mana Cost × Multiplier₁ × Multiplier₂ × Multiplier₃ × ... × MultiplierN
```

**Mana multipliers are MULTIPLICATIVE, not additive.**

### Comprehensive Mana Multiplier Table

| Support Gem | Mana Multiplier | Notes |
|-------------|-----------------|-------|
| Added Fire Damage | 130% | Reduced from 120% in v1.2.0 |
| Increased Critical Strikes | 120% | |
| Concentrated Effect | 140% | |
| Spell Echo | 150% | Reduced from 160% in v3.15.0d |
| Controlled Destruction | 150% | Increased from 130% in v3.15.0 |
| Brutality | 150% | Increased from 130% in v3.15.0 |
| Greater Multiple Projectiles | 160% | Reduced from 165% in v3.15.0 |
| Chain | 160% | Increased from 150% in v2.0.0 |
| Fork | 140% | Increased from 130% in v3.15.0 |

### Mana Multiplier Calculation Example
```
Base Skill Mana Cost: 50
Support Gems:
- Spell Echo (150%)
- Controlled Destruction (150%)
- Concentrated Effect (140%)

Final Mana Cost = 50 × 1.50 × 1.50 × 1.40
                = 50 × 3.15
                = 157.5 mana (rounded)
```

---

## Damage Calculation Formulas

### Core Damage Formula
```
Final Damage = Base Damage × (1 + ΣIncreased - ΣReduced) × Π(1 + More) × Π(1 - Less)
```

**Where:**
- **Base Damage:** The skill's base damage value
- **ΣIncreased:** Sum of all "increased" modifiers (additive)
- **ΣReduced:** Sum of all "reduced" modifiers (additive)
- **Π(1 + More):** Product of all "more" multipliers (multiplicative)
- **Π(1 - Less):** Product of all "less" multipliers (multiplicative)

### "More" vs "Increased" Mechanics

**Increased/Reduced (Additive):**
```
Total Modifier = 1 + (Increase₁ + Increase₂ + ... - Reduce₁ - Reduce₂ - ...)
```

**More/Less (Multiplicative):**
```
Total Multiplier = (1 + More₁) × (1 + More₂) × ... × (1 - Less₁) × (1 - Less₂) × ...
```

### Example Calculation
**Base Damage:** 1000
**Modifiers:**
- 100% increased damage from passive tree
- 50% increased damage from gear
- Support Gem A: 40% more damage
- Support Gem B: 30% more damage
- Support Gem C: 20% less damage

```
Final Damage = 1000 × (1 + 1.0 + 0.5) × (1 + 0.4) × (1 + 0.3) × (1 - 0.2)
             = 1000 × 2.5 × 1.4 × 1.3 × 0.8
             = 3,640 damage
```

---

## Support Gem Effectiveness

### Damage Effectiveness Formula
```
Effective Added Damage = Added Damage × Damage Effectiveness Percentage
```

**How it works:**
- All skills have a damage effectiveness value (default 100% if not listed)
- Added damage from support gems is multiplied by this value
- Skills with multiple hits often have reduced damage effectiveness for balance

**Example:**
- Skill has 50% damage effectiveness
- Support adds +10 fire damage
- Effective damage added = 10 × 0.50 = 5 fire damage

### Inheritance Property
Added damage fully becomes part of the affected skill and inherits ALL damage properties:
- Damage type conversions
- Scaling modifiers
- Critical strike rules
- All other skill-specific bonuses

---

## Support Gem Scaling Examples

### Increased Critical Strikes Support
**Mana Multiplier:** 120%

| Level | Crit Chance | Req. Level | Req. Intelligence |
|-------|-------------|------------|-------------------|
| 1 | 60% | 8 | 18 |
| 5 | 72% | 21 | 37 |
| 10 | 87% | 40 | 66 |
| 15 | 102% | 55 | 88 |
| 20 | 117% | 70 | 111 |

**Pattern:** Linear scaling, +3% crit chance per level

### Faster Casting Support
| Level | Cast Speed | Level | Cast Speed |
|-------|-----------|-------|-----------|
| 1 | 20% | 11 | 30% |
| 5 | 24% | 15 | 34% |
| 10 | 29% | 20 | 39% |

**Pattern:** +1% cast speed per level

### Added Fire Damage Support
**Mana Multiplier:** 130%
**Quality Bonus:** 0.5% increased fire damage per 1% quality

| Level | Physical as Extra Fire | Req. Level |
|-------|----------------------|------------|
| 1 | 25% | 8 |
| 10 | 34% | 40 |
| 20 | 44% | 70 |

**Pattern:** Approximately +1% per level

### Concentrated Effect Support
**Mana Multiplier:** 140%

- **Area of Effect:** 30% less (constant at all levels)
- **Area Damage:** 25% more (level 1) → 39% more (level 20)

### Greater Multiple Projectiles Support
**Mana Multiplier:** 160%
**Projectiles Added:** 4 additional projectiles

| Level | Less Projectile Damage |
|-------|----------------------|
| 1 | 35% |
| 10 | 31% |
| 20 | 26% |

**Pattern:** Damage penalty decreases by approximately 0.5% per level

### Chain Support
**Mana Multiplier:** 160%
**Chains Added:** +2 chains

| Level | Less Damage |
|-------|------------|
| 1 | 30% |
| 10 | 20% |
| 20 | 11% |

**Pattern:** Damage penalty decreases by approximately 1% per level

### Fork Support
**Mana Multiplier:** 140%
**Mechanic:** Projects fork at 120° angle upon hitting enemy

| Level | Damage Modifier |
|-------|----------------|
| 1 | 10% less |
| 11 | 0% (neutral) |
| 20 | 9% more |

**Pattern:** Scales from penalty to bonus, crossing zero at level 11

### Brutality Support
**Mana Multiplier:** 150%
**Restriction:** Supported skills cannot deal elemental or chaos damage

| Level | More Physical Damage |
|-------|---------------------|
| 1 | 40% |
| 10 | 49% |
| 20 | 59% |

**Pattern:** +1% per level

### Multistrike Support
**Mana Multiplier:** (Not specified in available data)
**Mechanic:** Repeats melee attack 2 additional times (3 total hits)

**Damage per Repeat:**
- First repeat: 40% more (level 1) → 50% more (level 20)
- Second repeat: 80% more (level 1) → 99% more (level 20)

**Attack Speed:** 35% more (level 1) → 44% more (level 20)
**Base Damage Penalty:** 20% less (level 1) → 10% less (level 20)

### Spell Echo Support
**Mana Multiplier:** 150%
**Mechanic:** Repeats spell once (2 total casts)

**Cast Speed:** 51% (level 1) → 80% (level 30)

**Important Notes:**
- Only the initial cast consumes mana
- Critical strike is rolled once for both casts
- Tooltip cast time is for single cast (actual time is 2x tooltip)

---

## Skill Gem Examples

### Fireball
**Damage Effectiveness:** 240% (changed from 180% in v3.11.0)
**Quality Bonus:** 1% increased projectile speed per 1% quality

| Level | Req. Level | Req. Int | Mana | Fire Damage | Ignite % | Radius |
|-------|-----------|----------|------|-------------|----------|--------|
| 1 | 1 | 0 | 6 | 9-14 | 20% | Base |
| 5 | 11 | 31 | 9 | 26-40 | 24% | +2 |
| 10 | 32 | 75 | 14 | 124-186 | 29% | +4 |
| 15 | 52 | 117 | 20 | 410-615 | 34% | +7 |
| 20 | 70 | 155 | 25 | 1095-1643 | 39% | +9 |

**Scaling Patterns:**
- Mana cost increases by approximately 1 per level
- Damage scales exponentially at higher levels
- Ignite chance increases by approximately 1% per level
- Area of effect increases periodically

### Raise Zombie
**Mana Cost:** 10 (level 1) → 44 (level 40)

**Key Scaling:**
- **Maximum Zombies:** 3 (levels 1-4) → 4 (level 5) → 8 (level 40)
- **Slam Cooldown Reduction:** Scales to 136% at level 40
- **Slam Area of Effect:** Scales to 136% at level 40 (76% at level 20)

**Experience Required (Level 20):** 342,000,000 total

---

## Gem Tags and Interactions

### How Gem Tags Work

**What Tags DO:**
- Categorize skills into groups
- Enable "+X Level of Socketed [tag] Gems" modifiers
- Help identify skill types for item modifiers

**What Tags DON'T DO:**
- Determine which support gems can support a skill
- Describe which stats apply to a skill
- Grant skills from items or threshold jewels

### Support Compatibility Rules
**Tags do NOT determine support gem compatibility.** Support compatibility is determined by the gem's internal rules, not by matching tags.

**Example:** A support gem with "Chaining" tag CAN support skills with "Projectile" tag, but this is coincidental, not rule-based.

### Tag Categories

**Damage Types:**
- Physical, Fire, Cold, Lightning, Chaos

**Skill Mechanics:**
- Attack, Spell, Cast, Channelling, Trigger

**Positioning/Delivery:**
- Melee, Projectile, Aura, Totem, Mine, Trap, Brand

**Special Mechanics:**
- Curse, Duration, Blink, Movement, Prismatic, Arcane

---

## Advanced Mechanics

### Cast Speed Calculation
```
Cast Speed (casts/second) = 1 / Cast Time (seconds)

Modified Cast Time = Base Cast Time / (1 + Cast Speed Increase %)
```

**Example:**
- Base cast time: 0.8 seconds
- Base cast speed: 1.25 casts/second
- With 50% increased cast speed:
  - Modified cast speed = 1.25 × 1.5 = 1.88 casts/second
  - Modified cast time = 0.8 / 1.5 = 0.53 seconds

**Frenzy Charges:** +4% cast speed per charge

### Curse Effectiveness
```
Curse Effect = (ΣAdded Effects) × (1 + ΣIncreases - ΣReductions) × Π(More) × Π(Less)
```

**Curse Types:**
- **Hexes:** Area of effect curses; bosses have 33-66% reduced effectiveness
- **Marks:** Single-target curses; only one mark can be active

**Doom Mechanic:**
- Self-cast hexes accumulate Doom over time
- Each Doom grants +1% curse effectiveness
- Default maximum: 30 Doom

**Curse Limits:**
- Default: 1 curse per enemy
- Can be increased through passives, items, ascendancies
- Theoretical maximum: 10 curses

### Aura Reservation

**Percentage-Based Auras:**
Most auras reserve a percentage of total mana pool.

**Flat-Based Auras:**
- Clarity
- Vitality
- Discipline

**Reservation Reduction Formula:**
```
Final Reservation = Base Reservation × (1 - Reduction₁) × (1 - Reduction₂) × ...
```

**Important:** Reservation reductions are MULTIPLICATIVE, not additive.

**Example:**
- Base reservation: 35%
- 20% reduced mana reserved
- Final = 35% × (1 - 0.20) = 35% × 0.80 = 28% (NOT 15%)

**Aura Effectiveness:**
- Only affected by the aura user's "Increased Effect of Auras" stat
- Allies cannot boost auras they receive
- Passive tree can provide up to 69% aura effect
- Ascendancies add 5-20% depending on choice

**Key Note:** Reduced Mana Cost support does NOT reduce aura reservations.

### Awakened Support Gems

**Characteristics:**
- Enhanced versions of standard support gems
- Level 1 awakened gem > Level 20 standard gem
- Higher starting level requirement
- Require more experience to level up
- Effects do NOT stack with normal versions
- Cannot use vendor quality recipe
- Maximum quality: 23% (through corruption only)

**Drop Sources:**
- Sirus
- The four Conquerors (Al-Hezmin, Veritania, Drox, Baran)

---

## Summary of Key Formulas

### Experience
```
Gem XP = Character XP × 0.10 (before penalties)
```

### Quality
```
Effective Bonus = floor(Base Effect × Quality %)
```

### Mana Cost
```
Final Mana = Base Mana × Mult₁ × Mult₂ × ... × MultN
```

### Damage
```
Final Damage = Base × (1 + ΣIncreased - ΣReduced) × Π(1 + More) × Π(1 - Less)
```

### Damage Effectiveness
```
Effective Added Damage = Added Damage × Effectiveness %
```

### Cast Speed
```
Cast Speed = 1 / Cast Time
Modified Time = Base Time / (1 + Speed Increase)
```

### Curse Effect
```
Effect = ΣAdded × (1 + ΣInc - ΣRed) × ΠMore × ΠLess
```

### Aura Reservation
```
Final Reserve = Base × (1 - Red₁) × (1 - Red₂) × ...
```

---

## Data Limitations

**Note:** The Path of Exile Wiki had multiple technical issues (Lua errors) preventing complete data extraction for:
- Some quality bonus percentages
- Complete experience tables for all gem levels
- Some mana multiplier values (missing from certain gem pages)
- Detailed attribute requirement formulas
- Some alternate quality variant specifics

For the most accurate and up-to-date information, refer to:
1. In-game gem tooltips
2. Official Path of Exile patch notes
3. Community tools like PoB (Path of Building)

---

## Research Sources
- https://pathofexile.fandom.com/wiki/Skill_gem
- https://pathofexile.fandom.com/wiki/Support_gem
- https://pathofexile.fandom.com/wiki/Gem_tag
- Various individual gem pages from the Path of Exile Wiki
- Accessed: 2025-10-22

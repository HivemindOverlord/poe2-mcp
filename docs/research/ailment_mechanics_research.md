# Path of Exile Ailment Mechanics - Comprehensive Research

## 1. IGNITE

### Base Damage Formula
```
Ignite DPS = 50% of base fire damage of the hit
Total Damage = 200% of base fire damage over base duration
```

### Duration Mechanics
- **Base Duration:** 4 seconds
- **Minimum Effective Duration:** 0.3 seconds (300ms) - applications below this are discarded
- **Scaling:** Duration increases extend the effect duration but maintain the same DPS (total damage increases proportionally)

### Damage Calculation Details
- Ignite damage scales from base fire damage **before** increased/more multipliers or resistance calculations
- The burning damage is calculated as: `50% of base fire damage per second`
- Total damage dealt: `200% of base fire damage` over 4 seconds

### Stacking Mechanics
- Multiple ignites **do not stack** cumulatively
- Only the highest DPS ignite deals damage at any moment
- Each ignite effect remains active until expiration
- Exception: Certain unique items can grant additional simultaneous ignite stacks

### Modifiers That Affect Ignite
Ignite damage is modified by:
- Damage
- Damage over Time
- Elemental Damage
- Fire Damage
- Burning Damage
- Ignite Damage
- Damage over Time Multiplier
- Fire Damage over Time Multiplier

**Note:** Attack, Spell, Melee, and Ranged damage modifiers do NOT apply to ignite

### Application Chance
- Critical strikes: 100% chance to ignite (inherent)
- Only fire damage inflicts ignite by default (equipment can modify this)

### Version History
- **Version 3.3.0:** Increased to 50% per second (from 40%)
- **Version 1.0.2:** Originally dealt 20% per second over 4 seconds

---

## 2. SHOCK

### Core Effect Formula
```
E = 1/2 × (D/T)^0.4 × (1 + M)
```

**Where:**
- **E** = Shock effect percentage (increased damage taken)
- **D** = Lightning damage dealt in the hit
- **T** = Enemy's ailment threshold (typically equals maximum life)
- **M** = Attacker's increases to shock effect (as decimal, e.g., 50% = 0.5)

### Base Values and Constraints
- **Base Duration:** 2 seconds
- **Minimum Effect:** 5% (shocks below this are discarded)
- **Maximum Effect:** 50% (can be exceeded with specific modifiers)
- **Minimum Damage Required:** 0.32% of ailment threshold to achieve 5% shock

### Ailment Threshold Mechanics
- **Standard monsters:** Ailment threshold = Maximum life
- **High-life bosses:** Use reduced thresholds
- **Example:** Sirus estimated at ~25 million damage threshold (~35% of boss life)

### Damage Scaling Examples
For standard ailment threshold (T = enemy max life):
- 5% shock requires: 0.32% of enemy max life as lightning damage
- Higher shocks require exponentially more damage due to the 0.4 exponent

### Modifier Scaling
Increases to shock effect reduce damage requirements proportionally:
- With 100% increased shock effect (M = 1.0): minimum shock requires only 0.06% of ailment threshold

### Application Mechanics
- Critical strikes: Always inflict shock (100% chance)
- Applies **after** hit damage calculation
- Only lightning damage inflicts shock by default (modifiable)
- Sources applying shock without damage: 15% base effect

---

## 3. FREEZE

### Duration Calculation Formula
```
Base Duration = 0.06 × (% of target max HP dealt as cold damage) seconds
```

**Constraints:**
- **Maximum Duration:** 3 seconds (achieved at 50% of target HP as cold damage)
- **Minimum Duration:** 0.3 seconds (freezes below this are discarded)

### Minimum Hit Requirement
```
Minimum Freeze = 5% of enemy maximum life as cold damage
```

**Calculation:**
- Freezes with duration < 0.3 seconds are discarded
- This effectively requires hitting for at least 5% of enemy life
- Example: Enemy with 20,000,000 HP requires minimum 1,000,000 cold damage

### Duration Examples
```
1% of max HP dealt   = 0.06 seconds (discarded - below minimum)
5% of max HP dealt   = 0.30 seconds (minimum freeze)
10% of max HP dealt  = 0.60 seconds
25% of max HP dealt  = 1.50 seconds
50% of max HP dealt  = 3.00 seconds (maximum)
100% of max HP dealt = 3.00 seconds (capped at maximum)
```

### Duration Modifiers
Freeze duration scales with:
- Freeze duration modifiers
- Ailment duration modifiers
- These increase duration and lower the minimum damage threshold

### Application Mechanics
- Critical strikes: 100% chance to freeze (inherent)
- Non-critical hits: Require explicit "chance to freeze" mechanics
- Only cold damage inflicts freeze by default (equipment can modify)

### Interaction with Chill
- When frozen, targets are simultaneously chilled
- Upon unfreezing, chill persists for an additional 0.3 seconds

---

## 4. CHILL

### Effect Magnitude Formula
```
E = 1/2 × (D/T)^0.4 × (1 + M)
```

**Where:**
- **E** = Chill effect (percentage reduction to action speed)
- **D** = Cold damage dealt in the hit
- **T** = Enemy's ailment threshold (typically equals maximum life)
- **M** = Sum of attacker's increases to chill effect (as decimal)

### Base Values and Constraints
- **Base Duration:** 2 seconds
- **Minimum Effect:** 5% action speed reduction (below this is discarded)
- **Maximum Effect:** 30% action speed reduction
- **Non-damage Chill:** 10% base effect (scales with modifiers)

### Damage Requirements for Chill Tiers
For standard ailment threshold (T = enemy max life):
```
5% chill  requires: 0.32%  of ailment threshold as cold damage
10% chill requires: 1.79%  of ailment threshold
20% chill requires: 10.12% of ailment threshold
30% chill requires: 27.89% of ailment threshold
```

### Modifier Scaling
Increases to chill effect apply **before** minimum/maximum enforcement:
- With 100% increased chill effect (M = 1.0):
  - Minimum requirement: 0.06% of ailment threshold
  - Maximum requirement: 4.93% of ailment threshold

### Application Mechanics
- Applies **after** hit damage calculation
- Multiple damage types can combine to determine chill magnitude
- Only cold damage inflicts chill by default (modifiable)

### Interaction with Freeze
- Frozen targets are considered chilled
- When freeze expires, chill persists for 0.3 seconds

---

## SHARED MECHANICS ACROSS AILMENTS

### Critical Strikes
- All ailments have 100% application chance on critical strikes
- No additional "chance to" modifier needed for crits

### Ailment Threshold
- For most monsters: Ailment Threshold = Maximum Life
- Bosses and high-life enemies: May use reduced thresholds
- Party scaling affects effective thresholds

### Duration Modifiers
All ailments can be scaled by:
- Specific ailment duration modifiers (e.g., "increased Freeze Duration")
- Generic "increased Ailment Duration" modifiers
- Skill effect duration modifiers (where applicable)

### Non-Linear Scaling
Shock and Chill use the formula: `(D/T)^0.4`
- This creates diminishing returns for effect magnitude
- Doubling damage does not double the effect
- The 0.4 exponent means large hits are needed for high-magnitude effects

### Minimum Thresholds
All ailments (except Ignite) have minimum thresholds:
- Freeze: 0.3 second duration (5% of max life)
- Shock: 5% effect (0.32% of ailment threshold)
- Chill: 5% effect (0.32% of ailment threshold)
- Ignite: 0.3 second duration

---

## FORMULAS QUICK REFERENCE

### Ignite
```
DPS = 50% of base fire damage
Total = 200% of base fire damage over 4 seconds
Min Duration = 0.3 seconds
```

### Shock
```
Effect = 1/2 × (Damage/Threshold)^0.4 × (1 + Modifiers)
Min Effect = 5%
Max Effect = 50%
Duration = 2 seconds
```

### Freeze
```
Duration = 0.06 × (% HP dealt) seconds
Min Duration = 0.3 seconds (5% HP)
Max Duration = 3 seconds (50% HP)
```

### Chill
```
Effect = 1/2 × (Damage/Threshold)^0.4 × (1 + Modifiers)
Min Effect = 5%
Max Effect = 30%
Duration = 2 seconds
```

---

## MATHEMATICAL NOTES

### The Power of 0.4 Exponent
For Shock and Chill formulas, the `^0.4` exponent creates specific scaling:
- To achieve 2x effect, need ~5.66x damage
- To achieve 3x effect, need ~15.59x damage
- This heavily penalizes scaling to maximum effect

### Threshold Bypass Calculations
To determine required damage for a specific effect:
```
D = T × (2E / (1 + M))^2.5
```
Where you solve for D given desired effect E

### Example Calculation
For 20% shock with no modifiers (M = 0):
```
D = T × (2 × 0.20 / 1)^2.5
D = T × 0.4^2.5
D = T × 0.1012
```
Requires 10.12% of ailment threshold as lightning damage

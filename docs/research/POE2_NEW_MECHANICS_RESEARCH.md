# Path of Exile 2 - New & Significantly Changed Mechanics

## Research Summary
This document contains comprehensive research on NEW and significantly different game mechanics in Path of Exile 2 compared to Path of Exile 1.

---

## 1. DODGE ROLL SYSTEM (ENTIRELY NEW)

### Core Mechanics
- **Default Movement Skill**: Available to ALL characters without requiring a gem slot
- **Distance**: Moves player 3.7 metres in chosen direction
- **No Cost/Cooldown**: By default, has no cooldown or resource cost
- **Animation Speed**: Cannot be modified by skill speed but IS affected by action speed
- **Movement Efficiency**: Covers more initial distance but travels same total distance as base movement speed

### Invulnerability Frames (i-frames)
- **Partial Damage Avoidance**: First half of roll animation avoids damage from projectiles and non-AoE attacks
- **Animation Canceling**: Can cancel almost any animation except another roll
- **Character Size**: Reduces to zero during animation, allowing navigation through tight enemy gaps
- **Vulnerability**: Still vulnerable if completely surrounded

### Modifiers & Interactions
- **Blink**: Replaces dodge roll with cooldown-based teleport spell
- **Bulwark Keystone**: Removes damage avoidance but grants consistent damage reduction
- **Unwavering Stance**: Disables dodge roll entirely, granting stun immunity instead
- **Cast on Dodge Meta Gem**: Gains Energy when you dodge roll and triggers socketed spells on reaching maximum Energy

### Unique Items
- **Surefooted Sigil**: +1 metre dodge roll distance
- **Ghostmarch**: Pass through enemies during dodge roll
- **Lioneye's Glare**: Variable distance based on recent usage

**WHY IT'S NEW**: Path of Exile 1 had NO dodge roll or active evasion mechanic. This is a completely new defensive layer adding skill-based gameplay.

---

## 2. SPIRIT RESOURCE SYSTEM (ENTIRELY NEW)

### What It Is
- **Dedicated Reserve Pool**: Used to activate and maintain skills with permanent effects
- **NOT Mana**: Separate resource from mana reservation system

### How to Obtain Spirit
- **Default**: Characters begin with 0 Spirit
- **Maximum**: Can accumulate up to 100 through quest rewards
- **Equipment Sources**:
  - Sceptres (primary source)
  - Body Armours
  - Amulets
- **Quest Rewards**: Three skull items grant +30 to +40 Spirit each
- **Passive Skills**: Various ascendancy classes offer Spirit bonuses

### What Spirit Powers
1. **Persistent Buff Effects**: Remain active continuously
2. **Permanent Minion Summoning**: Replaces temporary minion casting
3. **Trigger-Based Meta Gems**: Powers trigger mechanics

### Key Features
- **Item-Granted Buffs**: Persistent buffs and permanent minions granted by items do NOT reserve Spirit
- **Weapon Set Integration**: Each weapon set has independent Spirit pools
- **Skills Panel**: Toggle persistent abilities through dedicated UI

**WHY IT'S NEW**: Path of Exile 1 used mana reservation for auras and had temporary minions. Spirit is an entirely new resource that fundamentally changes build planning and persistent effect management.

---

## 3. DUAL STUN SYSTEM (MAJOR CHANGE)

### Two Stun Types

#### Light Stun
- **Frequency**: Brief interruptions occurring frequently
- **Trigger**: Any hit has chance to Light Stun based on damage dealt
- **Scaling**: 100% chance for hits dealing 100% of target max life
- **Threshold**: Chances below 15% are ignored
- **Effect**: Interrupts current action

#### Heavy Stun
- **Trigger**: Occurs when target's Stun bar fills completely
- **Effect**: Interrupts action AND prevents actions for several seconds
- **Duration**: Longer immobilization compared to Light Stun
- **Stun Bar**: Fills based on cumulative damage

### Damage Type Bonuses
- **Player Physical Damage**: 50% more Light Stun chance and Heavy Stun buildup
- **Player Melee Damage**: 50% more Light Stun chance and Heavy Stun buildup
- **Combined**: 125% bonus when using physical melee (multiplicative)
- **Monster Physical**: 100% more effectiveness
- **Monster Melee**: 33% more (233% combined with physical)

### Related Mechanics

#### Primed for Stun
- **State Trigger**: Activated at specific Heavy Stun buildup thresholds (40-70% depending on enemy rarity)
- **Purpose**: Enables powerful interactions with Crushing Blows

#### Crushing Blows
- **Mechanic**: Attacks that automatically trigger Heavy Stuns against Primed enemies
- **Synergy**: Creates strategic gameplay around stun threshold management

**WHY IT'S CHANGED**: Path of Exile 1 had a single stun mechanic. PoE2's dual-stun system with Light/Heavy Stuns, Primed state, and Crushing Blows creates much more complex and interactive stun gameplay.

---

## 4. FLASK SYSTEM OVERHAUL (MAJOR CHANGE)

### Core Differences from PoE1

#### Charge System
- **Combat Regeneration**: Charges regenerate through combat or checkpoints
- **Charge Gain by Enemy Rarity**:
  - Normal enemies: Half their Power value
  - Magic enemies: Full Power value
  - Rare/Unique enemies: Double their Power value
- **Refill Points**: Wells and Checkpoints completely refill flasks

#### Recovery Mechanics
- **Recovery Over Time**: Standard flasks provide gradual recovery (2-5 seconds typically)
- **NO Instant by Default**: Instant recovery only available on specific unique flasks with increased charge consumption
- **Persistent Effects**: Some flask effects continue "when Unreserved Life is Filled"

#### Rarity Restrictions
- **Limited Rarities**: Flasks can only be Normal, Magic, or Unique
- **NO Rare Flasks**: Unlike PoE1 where flasks could be rare

#### Charge Persistence
- **Unequipping Removes Charges**: "Unequipping a flask will remove all charges on the flask"

**WHY IT'S CHANGED**: Path of Exile 1 flasks refilled on killing enemies and many provided instant recovery. PoE2's charge-based system with recovery-over-time default creates more strategic flask management and reduces flask piano gameplay.

---

## 5. MANA REGENERATION CHANGES (MODIFIED)

### Key Differences from PoE1

#### Mana Consumption Timing
- **Throughout Execution**: Mana consumed during skill execution, not upon activation
- **Cancellation Benefit**: Canceling a skill or being stunned WON'T deplete mana pool

#### Base Statistics
- **Starting Mana**: 34 at level 1
- **Per Level**: +4 maximum mana per player level
- **Intelligence Scaling**: +2 maximum mana per point of Intelligence
- **Base Regeneration**: 4% of maximum mana (constant across all levels)

#### Mana States
- **Low Mana**: Triggered at 35% of maximum or below
- **Full Mana**: Achieved at 100% (or higher through overflow), unless mana is reserved

#### Related Mechanics
- **Mana Recouping**: Damage taken can restore mana before affecting life pools
- **Damage from Mana**: Mechanics like Cloak of Defiance: "30% of Damage is taken from Mana before Life"

**WHY IT'S CHANGED**: Mana consumption during execution (not activation) prevents mana waste from interruptions, making combat more forgiving.

---

## 6. WEAPON SET SYSTEM (SIGNIFICANTLY EXPANDED)

### Core Features
- **Two Independent Sets**: Main hand and off hand equipment in both sets
- **Automatic Skill Assignment**: Skills use currently active set if possible, or automatically swap if required
- **NO Shared Cooldown**: Unlike PoE1's basic weapon swap

### Dedicated Passive Points
- **Weapon Set Passive Skill Points**: Can be allocated DIFFERENTLY in each Weapon Set Passive Tree
- **Total Points**: 24 total points available per weapon set
- **Acquisition**: Earned by defeating bosses and completing quests across five acts

### Spirit Management
- **Independent Spirit Pools**: Each weapon set can have varying Spirit reserves
- **Equipment-Based**: Based on equipped weapons (like Sceptres) and active persistent skills

### Shared Equipment Option (v0.3.0)
- **Cross-Set Assignment**: Can assign same weapon(s) to both weapon sets instead of requiring different items

**WHY IT'S EXPANDED**: Path of Exile 1 had basic weapon swap. PoE2's weapon sets with dedicated passive trees, automatic skill swapping, and independent Spirit pools create true dual-build capability on one character.

---

## 7. META GEM SYSTEM (ENTIRELY NEW)

### What They Are
- **Skill Containers**: Specialized skill gems that allow socketing other active skills as support gems
- **Fundamental Change**: Other active skills function as "support gems" within meta gems

### Core Mechanics

#### Skill Integration
- **Shared Supports**: "Support gems socketed in a meta gem will support the meta gem and any other compatible socketed skill gems"
- **Multiple Skills**: Single meta gem can coordinate multiple skills simultaneously

#### Triggering Systems
- **Trigger Definition**: "A Skill occurs immediately, without attack or cast time, and usually targets the cause of the trigger"
- **Various Triggers**: Blocking, killing, dodging, critical hits, casting, etc.

#### Energy System
- **Trigger Frequency**: Most trigger-based meta gems use Energy counter to balance trigger frequency
- **Independent Counters**: Each meta gem builds energy independently, even if multiple copies of same meta gem
- **Trigger Conditions**: Accumulates through specific actions depending on meta gem type

### Examples
- **Spellslinger**: Triggers spells when sufficient energy accumulates from casting
- **Blasphemy**: Converts socketed curse skills into auras affecting nearby enemies
- **Cast on Block**: Triggers spells when blocking attacks
- **Cast on Dodge**: Triggers spells when dodge rolling
- **Ancestral Warrior Totem**: Creates totem using socketed mace skills
- **Reaper's Invocation**: Gains energy from killing enemies with melee attacks
- **Invocation Skills**: Store energy until manually activated, then trigger multiple times based on stored energy

**WHY IT'S NEW**: Path of Exile 1 had trigger gems like Cast on Critical Strike, but they were support gems. Meta gems are an entirely new category that fundamentally changes how skills interact and trigger.

---

## 8. ENERGY SYSTEM (NEW - FOR META GEMS)

### Core Function
- **Meta Gem Resource**: Specific to Meta gems for determining trigger frequency
- **Independent per Skill**: "Skills generate and use Energy" with each skill maintaining "its own Energy count particular to that Skill"

### How It Works
- **Action-Based Accumulation**: Varies by Meta gem type (casting spells, blocking, critical hits, killing enemies, dodging)
- **Maximum Trigger**: When energy reaches maximum capacity, socketed spells trigger simultaneously
- **Reset**: Counter resets after triggering

### Key Restrictions
- **No Triggered Skill Generation**: "Energy cannot be gained from direct effects of Triggered Skills"
- **Independent Counters**: Multiple Meta gems build energy independently, "even if multiple copies of the same meta gem are used"
- **Shared Trigger**: Multiple socketed skills share combined energy and trigger together

### Invocation Variant
- **Manual Activation**: Don't trigger immediately at max energy
- **Storage System**: Store energy until manually activated
- **Multiple Triggers**: "Trigger socketed spells a number of times based on total amount of energy stored"

### Distinction
- **NOT Energy Shield**: Energy is trigger resource system, Energy Shield is damage absorption (separate mechanics)

**WHY IT'S NEW**: This Energy system for Meta gems is entirely new to PoE2, creating a resource-based trigger system that didn't exist in PoE1.

---

## 9. HONOUR SYSTEM (NEW - TRIAL OF SEKHEMAS)

### What It Is
- **Trial-Specific Resource**: Additional resource managed within Trial of the Sekhemas
- **Damage Absorption**: "A percentage of damage you take from enemies in the Trial will be taken from your Honour"
- **Failure Condition**: "If your Honour reaches zero then the Trial is failed"

### Initial Pool
- **Based on Character Stats**: Calculated from maximum life and energy shield combined
- **Mind over Matter**: If active, maximum mana is also included

### Gaining Honour
- **Trading**: Use Sacred Water with the Merchant
- **Shrines**: Venerate certain Maraketh Shrines
- **Boons**: "Earned Honour" restores honour upon room completion
- **Maximum Honour**: Gaining maximum honour also restores current honour

### Losing Honour
- **Monster Hits**: Suffer hits from monsters
- **Traps**: Take damage from environmental hazards
- **Proximity Bonus**: "Closer proximity to monsters reduces Honour lost on hit, up to 35% less in close range"

### Honour Resistance
- **Mitigation Stat**: Reduces damage taken to Honour
- **Maximum**: 75% Honour Resistance cap
- **Sources**: Obtainable through trial-specific modifiers and boons

**WHY IT'S NEW**: This creates a gauntlet-style endgame challenge with secondary survival resource, completely unique to PoE2.

---

## 10. CHARM SYSTEM (ENTIRELY NEW)

### What They Are
- **Defensive Trinkets**: Automatically trigger protective effects when conditions met
- **Similar to Flasks**: Function "somewhat similarly to utility flasks" but distinct system

### How They Work

#### Activation
- **Automatic Only**: CANNOT be manually activated
- **Condition-Based**: Trigger when conditions satisfied and charges available
- **Duration-Based**: Provide benefit for specified duration

#### Charge System
- **Gaining Charges**:
  - Killing monsters (half the monster's Power value)
  - Using Wells
  - Activating Checkpoints
- **Capacity**: Typically 40-80 charges depending on charm type

#### Equipment Limitations
- **Maximum**: 3 charms can be equipped simultaneously
- **Primary Source**: Belts grant 1-3 charm slots depending on item level
- **Additional Slots**: Obtainable through specific passive skills and unique items

#### Quality Mechanic
- **Duration Increase**: Quality on charms increases effect duration by quality percentage

### Base Charm Types (13 Total)
- **Resistance Boosts**: Ruby, Sapphire, Topaz
- **Status Immunities**: Stone, Silver, Thawing, Staunching, Antidote, Dousing, Grounding
- **Special Effects**: Amethyst, Cleansing, Golden

**WHY IT'S NEW**: Charms are an entirely new defensive item category that didn't exist in PoE1, providing automatic condition-based defenses.

---

## 11. RUNE SYSTEM (ENTIRELY NEW)

### What They Are
- **Socketable Modifiers**: Items that add additional modifiers to equipment
- **Permanent Installation**: "A Rune cannot be removed" once socketed
- **Replaceable**: Can replace by placing another socketable item in same socket

### Equipment Compatibility
- **Weapons**: Martial weapons, staves, wands
- **Armor**: Helmets, gloves, boots, body armor

### Tier Progression
1. **Lesser Runes**: Drop until level 31
2. **Regular Runes**: Drop until level 52
3. **Greater Runes**: Drop in endgame
4. **Endgame/Special Runes**: Map-exclusive drops

### Upgrading
- **Reforging Bench**: Combine three identical runes into one higher-tier version
- **Progressive Power**: Higher tiers provide stronger modifiers

**WHY IT'S NEW**: Runes introduce permanent, stackable equipment customization layer separate from skill gems or passives, entirely new to PoE2.

---

## 12. SKILL GEM SYSTEM OVERHAUL (MAJOR CHANGES)

### Key Changes from PoE1

#### Socketing Revolution
- **No Item Sockets**: Gems are NOT socketed into armor/weapons (major change from PoE1)
- **Skill Limit**: "Up to 9 skill gems can be bound simultaneously by default"
- **No Multiple Copies (v0.3.0)**: "You can no longer socket multiple copies of the same Skill Gem into your main skill sockets"

#### Support Gem Limitations
- **Attribute-Based Limits**: Support gems limited by character attributes (5 points = 1 support of that color)
- **Per-Skill Limit**: Each skill has 2 support slots by default, expandable to 5 via Jeweller's Orbs
- **Category Restriction**: "You cannot have multiple support gems that share same category socketed to same skill"
- **No Per-Character Limit (v0.3.0)**: Removed restriction of one support per character - "You can use as many copies as you like"

#### Support Gem Tiers (v0.3.0)
- **Multiple Tiers**: "Many Supports now have multiple tiers as you progress through the game"
- **Progressive Power**: Different stat values, additional stats, or different functionality
- **Lineage Supports**: Cannot be crafted, only drop from core pool or specific bosses

#### Spirit Gems
- **New Category**: Special persistent buff skills requiring Spirit reservation
- **Support Compatibility**: Can be supported by support gems (increases reservation cost)
- **Reservation Stacking**: "Only one copy per rank of support gems that add spirit reservation is allowed across all your skills"

#### Attribute Requirements
- **Reduced Requirements**: Endgame skill gems received ~20-25% lower attribute requirements on average

**WHY IT'S CHANGED**: Path of Exile 1 socketed gems into equipment. PoE2's separated gem system with skill limits, attribute-based support limits, and tiered supports fundamentally changes build construction.

---

## 13. PERSISTENT MINION SYSTEM (MAJOR CHANGE)

### Core Mechanic
- **Continuous Summoning**: "Persistent Minions will reserve a portion of Spirit while active"
- **NOT Temporary**: Remain active continuously unlike PoE1's temporary minions

### Spirit Integration
- **Reserve System**: Minions consume Spirit instead of upfront mana costs
- **Skills Panel**: Selected and maintained through Skills Panel
- **Variable Pools**: "Weapon Sets can have differing amounts of available Spirit, due to weapons with Spirit (such as Sceptres), Weapon Set Passive Skills, or Persistent Skills active in specific Weapon Sets"

### Automatic Revival
- **Self-Resurrection**: "Permanent minions will revive themselves automatically if no other allied reviving minions have died within 7.5 seconds"
- **NO Manual Re-summoning**: Creates sustainable army without recasting

### Dual System
- **Persistent Minions**:
  - Require Spirit reservation
  - Auto-revive
  - Selected in skill menu
- **Temporary Minions**:
  - Use upfront mana costs
  - Don't self-revive
  - Manual summoning

**WHY IT'S CHANGED**: Path of Exile 1 required constant re-summoning of minions using mana. PoE2's persistent minion system with Spirit reservation and auto-revival completely changes summoner gameplay to be more sustainable and less micro-management intensive.

---

## 14. ACTIVE BLOCK SYSTEM (MAJOR CHANGE)

### Two Block Types

#### Passive Block
- **Automatic Application**: Applied with percentage chance to blockable hits from any direction
- **Shield Source**: Primarily obtained from shields
- **Maximum Cap**: 50% block chance (reduced from 75% in v0.3.0)
- **Full Prevention**: "Completely prevents damage of an incoming Hit"

#### Active Block (NEW TO POE2)
- **Skill-Based**: Activated through shield skills like Raise Shield or Parry
- **Directional**: Provides guaranteed blocking when shield faces attacker
- **Drawback**: "Blocking hits through Active Block will build up your Player Heavy Stun meter"
- **Heavy Stun Consequence**: When meter fills, causes 3-second heavy stun

### Universal Blocking
- **All Hit Types (v0.3.0)**: Block now applies to all non-unblockable hits
- **Previous Limitation**: Was limited to strikes and projectiles
- **Unblockable Attacks**: Boss abilities signaled by "red glow and audio cue during windup"

### Blocking Limitations
- **Debuff Persistence**: Players still take associated debuffs like Stun and Freeze from blocked attacks
- **Stun/Freeze Lock**: "You can't Block while Stunned or Frozen"

### Balance Changes (v0.3.0)
- **Maximum Reduction**: 75% → 50%
- **Modifier Reduction**: Shield block chance modifiers reduced from 7 to 3
- **Maximum Tier**: Now 30%

**WHY IT'S CHANGED**: Path of Exile 1 only had passive block chance. PoE2's Active Block system with directional blocking, stun meter buildup, and skill-based activation adds skill expression to blocking.

---

## 15. ASCENDANCY SYSTEM CHANGES (MODIFIED)

### Availability
- **Current**: 17 regular Ascendancy classes
- **Planned**: 3 Ascendancies per class at full release (36 total)
- **NOT Chosen at Creation**: Unlocked by completing Ascension Trials

### Point System
- **Points per Trial**: 2 Ascendancy Skill Points per trial completion
- **Maximum**: 8 points total
- **Repeatable Trials**: Can repeat trials to earn all points from single trial type

### Flexibility Changes
- **Any Order**: "Trials can be completed in any order"
- **Multiple Sets**: "Possible to earn multiple sets of points in single run if you haven't completed lower difficulty trials"
- **Respeccing**: Change Ascendancy class by completing trial matching current progression level, then using Altar of Ascendancy with all passives unallocated

### Alternate Ascendancies (NEW)
- **Unlock Method**: "Alternate versions of existing ascendancy classes...through various encounters"
- **Example**: Abyssal Lich requires already ascending to base Lich class first
- **Additional Depth**: Provides variant builds within same ascendancy

**WHY IT'S CHANGED**: More flexible trial system, respeccing capability, and alternate ascendancies provide more build diversity and experimentation than PoE1's rigid system.

---

## 16. ELEMENTAL AILMENT THRESHOLD CHANGES (MODIFIED)

### Ailment Types
- **Ignite** (Fire): 20% of fire damage dealt as DoT
- **Chill** (Cold): Slows targets based on damage dealt
- **Freeze** (Cold): Incapacitates for 4 seconds
- **Shock** (Lightning): 20% increased damage taken
- **Electrocute** (Lightning): Interrupts and immobilizes targets

### Major Threshold Change (v0.2.0)
- **Player Base Ailment Threshold**: NOW half of Maximum Life
- **Previous**: ALL of Maximum Life
- **Effect**: Players are now HARDER to inflict ailments on compared to PoE1

### Spreading Ailments (NEW MECHANIC)
- **Definition**: "Spreading an ailment inflicts a new, matching ailment on another target, from the same source"
- **Purpose**: Propagate elemental effects across enemy groups with controlled restrictions

**WHY IT'S CHANGED**: Reduced player vulnerability to ailments makes the game more forgiving, while ailment spreading adds new offensive mechanics.

---

## 17. CURRENCY SYSTEM OVERHAUL (MAJOR CHANGES)

### Tiered Hierarchy (NEW)
- **Organization**: Regular, Greater, and Perfect tiers
- **Conversion**: "Greater currency can be broken down into stack of 3 of the regular version"
- **PoE1 Comparison**: Original game had flat currency system

### New Currency Mechanics

#### Hinekora's Lock
- **Function**: "Allows item to foresee result of next Currency item used on it"
- **Strategic Crafting**: Preview mechanic for informed decisions
- **PoE1 Comparison**: Didn't exist

#### Fracturing Orb
- **Function**: "Fracture random modifier on rare item with at least 4 modifiers, locking it in place"
- **Permanent Locking**: Introduces modifier preservation to crafting

### Essence Expansion
- **Greater/Lesser Variants**: Essence system has progression tiers
- **Example**: Lesser Essence of Abrasion vs standard version with different power levels

### Drop Level Adjustments
- **High-Level Equity**: "Between item levels 78-80, and even further between 81-82, this percentage increases significantly"
- **Tier Promotion**: Reduces lower-tier currency drops in favor of higher tiers

**WHY IT'S CHANGED**: Tiered currency system, preview mechanics, and fracturing create more strategic crafting than PoE1's simpler currency system.

---

## 18. CHARACTER CLASS EXPANSION (EXPANDED)

### Total Classes
- **12 Playable Classes**: Doubled from PoE1's 6 base classes
- **Organization**: Six pairs, each pair sharing same character with different backstories

### Class Pairs by Attributes
- **Strength**: Marauder, Warrior
- **Dexterity**: Ranger, Huntress
- **Intelligence**: Witch, Sorceress
- **Strength/Dexterity**: Duelist, Mercenary
- **Dexterity/Intelligence**: Shadow, Monk
- **Strength/Intelligence**: Templar, Druid

### Naming Consideration
- **Original Plan**: Rename Duelist/Shadow to Gladiator/Assassin
- **Reversed**: Decision reversed before Early Access to maintain naming continuity with PoE1

**WHY IT'S EXPANDED**: Doubles available starting classes, providing more build identity and ascendancy options from character creation.

---

## 19. PASSIVE SKILL TREE CHANGES (MODIFIED)

### Structure
- **Central Hub**: Circular starting area with clusters spreading outward
- **Attribute Organization**: Strength (southwest), Dexterity (southeast), Intelligence (north)
- **Hybrid Passives**: Between attribute sections

### Node Types
- **Attribute Nodes**: "+5 to any attribute selected" and can be changed for reduced cost
- **Small Passives**: Minor stat bonuses
- **Notable Passives**: Significant power boosts
- **Jewel Sockets**: Enable modular jewel socketing
- **Keystones**: Dramatic mechanical alterations with powerful effects and drawbacks

### New PoE2 Mechanics

#### Weapon Specialization
- **Separate Allocation**: Per weapon set skill point allocation
- **24 Potential Points**: Dedicated weapon set passive points

#### Ascendancy Trees
- **Sub-Trees**: Specialized trees after Ascension
- **8 Points Maximum**: Per character

#### Interactive Elements
- **Liquid Emotions**: "From Delirium encounters can be used to Instil an amulet" to allocate notables without spending points

### Progression
- **Level Points**: One skill point per level (up to 99)
- **Quest Points**: 24 from quests
- **Total**: 123 potential allocations

**WHY IT'S MODIFIED**: Weapon set passive trees, amulet instilling, and respeccing improvements add flexibility compared to PoE1.

---

## 20. ATTRIBUTE SYSTEM CHANGES (MODIFIED)

### Core Attributes
- **Strength**: +2 maximum Life per 1 Strength
- **Dexterity**: +5 Accuracy Rating per 1 Dexterity
- **Intelligence**: +2 maximum Mana per 1 Intelligence

### Key Philosophy
- **Requirement-Focused**: "Attributes do NOT grant damage to Skills or any other benefits except where specifically stated"
- **Different from PoE1**: Less direct combat scaling

### Support Gem Limits (NEW TO POE2)
- **Attribute-Based Capacity**: 5 points of stat = 1 support of corresponding color
- **Red**: Strength-based supports
- **Green**: Dexterity-based supports
- **Blue**: Intelligence-based supports

### Balance Changes (v0.3.0)
- **Equipment Requirements**: ~20-25% lower attribute requirements on endgame base types
- **Skill Gem Requirements**: Similar reductions
- **Accessibility**: Easier to use off-attribute skills

**WHY IT'S CHANGED**: Support gem capacity tied to attributes creates new strategic consideration for attribute planning beyond just equipment requirements.

---

## 21. TRIAL OF THE SEKHEMAS (ENTIRELY NEW ENDGAME)

### What It Is
- **Ascension Trial**: Randomized endgame challenge introduced in Act 2
- **Entry Requirement**: Insert Djinn Barya (trial key) into Relic Altar at designated waypoint

### Structure
- **4 Floors**: 8 rooms per floor (32 total rooms)
- **Room Types**:
  - **Chalice**: Defeat rare monsters
  - **Escape**: Disable death crystals before timer expires
  - **Ritual**: Eliminate casters spawning reinforcements
  - **Gauntlet**: Navigate trap circuits using colored levers
  - **Hourglass**: Survive spawning enemies until time runs out
  - **Boss**: Defeat floor guardians

### Honour System (See Section 9)
- **Trial Health Pool**: Calculated from max life, energy shield, and mana (if applicable)
- **Damage Transfer**: Damage taken goes to Honour instead of actual health
- **Failure**: Trial ends when Honour reaches zero
- **Maximum Resistance**: Up to 75% Honour Resistance through relics

### Resource Management

#### Sacred Water
- **Trial Currency**: Purchase Boons, recover Honour, obtain relics
- **Sources**: Fountains, defeated enemies, chests

#### Boons
- **Beneficial Effects**: Purchased with Sacred Water
- **Examples**: Honour recovery, increased maximum Honour, combat bonuses

### Progression & Rewards
- **Floor Completion**: Unlocks Relic Altar inventory slots
- **Ascendancy Points**: Grants ascendancy progression
- **Tier Progression**: Higher-tier keys (area levels 45+, 60+, 75+)
- **Rewards**: Unique items, Grand Spectrum jewels

**WHY IT'S NEW**: Gauntlet-style roguelike trial with Honour system, Sacred Water economy, and room variety provides completely new endgame challenge type not in PoE1.

---

## 22. ENDGAME STRUCTURE (MODIFIED)

### Location
- **The Ziggurat Refuge**: Endgame hub after story completion
- **Objective**: "Work with Doryani and traverse across Wraeclast using Map Device to undo damage the Cataclysm caused"

### Systems
- **The Atlas**: Map progression system
- **Map Device**: For accessing endgame content
- **Waystone System**: For map progression (see Section 23)
- **Multiple Encounter Types**: Breach, Abyss, Expedition, Ritual, etc.
- **Pinnacle Encounters**: Specialized boss fights with splinter-based entry

**WHY IT'S MODIFIED**: While structurally similar to PoE1's endgame, Waystone system and encounter integration provide different progression feel.

---

## 23. WAYSTONE SYSTEM (REPLACES MAPS)

### What They Are
- **Consumable Items**: Used in Map Device to open portals to maps
- **Tier System**: Tier 1 (area level 65) to Tier 16 (area level 80)

### Portal Mechanics
- **Up to 6 Portals**: Depending on modifiers
- **Free Entry/Exit**: Enter and exit without consuming portals
- **Death Penalty**: "Dying will consume a portal"
- **Reusability**: Once all portals used, need new waystone

### Modifications
- **Craftable**: "Can roll affixes that become area modifiers in opened map"
- **Risk/Reward**: Modifications increase difficulty but provide bonuses (drop rates, item rarity)
- **Unidentified Bonus**: "30% increased Waystone drop chance" when using unidentified waystone

### Tier Scaling
- **Monster Levels**: Higher tiers = higher monster levels
- **Rewards**: Greater challenges = better item drops

**WHY IT'S DIFFERENT**: While functionally similar to PoE1's Maps, Waystones appear to have different naming, modification systems, and potentially different acquisition methods.

---

## 24. BREACH MECHANICS (MODIFIED)

### Core Mechanics
- **Expanding Tears**: "Breach monsters can only be seen and damaged inside expanding Breach"
- **Duration Scaling**: "Breach will continue to expand for specified duration before closing in on itself"
- **Performance Reward**: Defeating more monsters keeps Breach open longer

### Features

#### Clasped Hands
- **Interactive Objects**: Drop rewards when walked over
- **Rewards**: Breach Splinters, Rings, Catalysts

#### Splinter System
- **Collection**: From defeated monsters and Clasped Hands
- **Entry Requirement**: "Consume at least 50 Splinters at Realmgate to enter Twisted Domain"

### Changes (v0.2.0)
- **Monster Spawning**: Reduced overall
- **Spawn Timing**: Higher percentage spawn earlier
- **Chest Frequency**: Small Breach chests decreased
- **Splinter Availability**: Obtainable from all map tiers with scaling rewards

**WHY IT'S MODIFIED**: Streamlined encounter pacing and rewards compared to PoE1's Breach implementation.

---

## 25. EXPERIENCE & DEATH PENALTY (MODIFIED)

### Experience Gain
- **Monster Kills**: Amount varies by monster level and rarity
- **Progressive Scaling**: Each level requires increasingly more experience

### Death Penalty
- **Map Device Areas**: "Characters lose amount of experience equal to 10% of current level if they die in any area accessed by map device"
- **Safeguard**: Loss "cannot result in change of character level" (won't be demoted)

**WHY IT'S RELEVANT**: Death penalty exists but with level protection, different from PoE1's implementation.

---

## 26. COOLDOWN SYSTEM (SIMILAR BUT EXPANDED)

### Core Concept
- **Timer Prevention**: Prevents skill reactivation after use
- **Example**: "If skill has 5 second cooldown, then after it is used, it cannot be used again for 5 seconds afterwards"

### Cooldown Recovery Rate
- **Modification Stat**: Divides cooldown duration
- **Example**: "With 100% increased Cooldown Recovery Rate your Skill cooldowns will effectively be halved"

### Timing Mechanics
- **Standard**: Most cooldowns begin on activation
- **Conditional**: Some don't begin "until some condition is met, such as skill's duration expiring"

### Related Items
- **Sands of Silk**: (15-30)% increased Cooldown Recovery Rate
- **Crest of Ardura**: (30-50)% increased Cooldown Recovery Rate
- **Temporalis**: Skills have (-2--1) seconds to Cooldown

**WHY IT'S SIMILAR**: Functionally similar to PoE1 but with expanded unique item interactions.

---

## SUMMARY OF MAJOR NEW SYSTEMS

### ENTIRELY NEW TO POE2
1. **Dodge Roll** - Skill-based defensive mechanic with i-frames
2. **Spirit Resource** - Dedicated pool for persistent effects
3. **Meta Gems** - Skill container system
4. **Energy System** - Trigger resource for Meta gems
5. **Honour System** - Trial-specific survival resource
6. **Charms** - Automatic defensive trinkets
7. **Runes** - Permanent equipment modifiers
8. **Active Block** - Skill-based directional blocking
9. **Persistent Minions** - Continuous summoning with Spirit
10. **Trial of the Sekhemas** - Gauntlet-style endgame
11. **Alternate Ascendancies** - Variant ascendancy unlocks

### MAJOR CHANGES FROM POE1
1. **Dual Stun System** - Light Stun + Heavy Stun with Primed/Crushing mechanics
2. **Flask Overhaul** - Charge-based with recovery-over-time default
3. **Weapon Sets** - Dedicated passive trees and independent Spirit pools
4. **Skill Gem System** - Not socketed in equipment, attribute-limited supports
5. **Support Gem Tiers** - Progressive power scaling
6. **Currency Tiers** - Regular/Greater/Perfect hierarchy
7. **Mana Consumption** - During execution not activation
8. **Elemental Ailment Threshold** - Halved for players (harder to ailment)
9. **Character Classes** - Doubled to 12 classes
10. **Ascendancy Flexibility** - Any order, respeccing, alternate versions
11. **Attribute System** - Support gem capacity tied to attributes
12. **Block System** - Active + Passive with stun meter
13. **Waystone System** - Replaces Maps with different mechanics

---

## KEY TAKEAWAYS FOR ENHANCEMENT SERVICE

### Most Impactful New Mechanics
1. **Dodge Roll** - Requires tracking i-frames, cooldowns, distance, modifiers
2. **Spirit** - New resource to track alongside Life/Mana/ES
3. **Dual Stun System** - Track Light/Heavy stun, Primed state, stun bar
4. **Meta Gems + Energy** - Complex trigger system tracking
5. **Weapon Sets** - Dual build management with independent passives/Spirit
6. **Charms** - Automatic trigger condition tracking
7. **Trial of Sekhemas** - Honour tracking, Sacred Water economy
8. **Persistent Minions** - Spirit reservation and auto-revival tracking

### Build Calculation Implications
- **Spirit Pool Calculation** - Equipment, quests, passives
- **Support Gem Limits** - Based on attribute totals
- **Weapon Set Passive Trees** - Separate calculations per set
- **Active Block Stun Meter** - Track stun buildup
- **Honour System** - Calculate from Life/ES/Mana
- **Energy Generation** - Per Meta gem based on action type
- **Charm Charge Tracking** - Based on monster kills
- **Stun Threshold Calculations** - Light vs Heavy with Primed states

### New Data Requirements
- Dodge roll modifiers (distance, i-frame duration, replacements)
- Spirit sources (equipment, quests, passives, ascendancies)
- Meta gem Energy generation rates
- Charm types, triggers, and capacities
- Rune modifiers by tier
- Weapon set passive tree data
- Support gem tiers and progression
- Honour resistance and calculation
- Ailment threshold changes
- Active block stun meter mechanics

---

## Research Sources
- https://www.poe2wiki.net/wiki/Dodge_Roll
- https://www.poe2wiki.net/wiki/Spirit
- https://www.poe2wiki.net/wiki/Stun
- https://www.poe2wiki.net/wiki/Flask
- https://www.poe2wiki.net/wiki/Mana
- https://www.poe2wiki.net/wiki/Energy
- https://www.poe2wiki.net/wiki/Honour
- https://www.poe2wiki.net/wiki/Weapon_set
- https://www.poe2wiki.net/wiki/Meta_gem
- https://www.poe2wiki.net/wiki/Skill_gem
- https://www.poe2wiki.net/wiki/Support_gem
- https://www.poe2wiki.net/wiki/Charm
- https://www.poe2wiki.net/wiki/Rune
- https://www.poe2wiki.net/wiki/Minion
- https://www.poe2wiki.net/wiki/Block
- https://www.poe2wiki.net/wiki/Ascendancy_class
- https://www.poe2wiki.net/wiki/Character_class
- https://www.poe2wiki.net/wiki/Waystone
- https://www.poe2wiki.net/wiki/Breach
- https://www.poe2wiki.net/wiki/Experience
- https://www.poe2wiki.net/wiki/Endgame
- https://www.poe2wiki.net/wiki/Trial_of_the_Sekhemas
- https://www.poe2wiki.net/wiki/Passive_skill
- https://www.poe2wiki.net/wiki/Attribute
- https://www.poe2wiki.net/wiki/Currency
- https://www.poe2wiki.net/wiki/Elemental_ailment
- https://www.poe2wiki.net/wiki/Cooldown

**Research Date**: 2025-10-22
**Game Version Referenced**: Early Access (v0.3.0 and earlier patch notes)

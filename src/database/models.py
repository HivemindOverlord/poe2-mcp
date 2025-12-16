"""
SQLAlchemy database models for PoE2 game data
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Item(Base):
    """Item base types and data"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    base_type = Column(String, nullable=False)
    item_class = Column(String, nullable=False, index=True)
    rarity = Column(String)  # normal, magic, rare, unique
    item_level = Column(Integer)
    required_level = Column(Integer)
    properties = Column(JSON)  # Dict of properties
    requirements = Column(JSON)  # Stat requirements
    implicit_mods = Column(JSON)  # List of implicit modifiers
    explicit_mods = Column(JSON)  # List of explicit modifiers
    flavour_text = Column(Text)
    is_corrupted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UniqueItem(Base):
    """Unique item data"""
    __tablename__ = "unique_items"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    base_type = Column(String, nullable=False)
    item_class = Column(String, nullable=False, index=True)  # Helmet, Body Armour, Weapon, etc.
    required_level = Column(Integer)  # Alias for level_requirement
    level_requirement = Column(Integer)  # Alternative name used by scripts
    modifiers = Column(JSON)  # List of unique modifiers (alias for mods)
    mods = Column(JSON)  # Alternative name for modifiers
    stats = Column(JSON)  # Item stats including chaos_value
    flavour_text = Column(Text)
    description = Column(Text)  # Additional description
    drop_level = Column(Integer)
    rarity_tier = Column(Integer)  # 1-5
    tags = Column(JSON)  # List of tags (e.g., ["caster", "spell_damage"])
    created_at = Column(DateTime, default=datetime.utcnow)


class Modifier(Base):
    """Item and passive modifiers"""
    __tablename__ = "modifiers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    mod_type = Column(String, nullable=False)  # prefix, suffix, implicit, explicit
    stat_text = Column(Text)
    min_value = Column(Float)
    max_value = Column(Float)
    tags = Column(JSON)
    tier = Column(Integer)
    item_level_requirement = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class PassiveNode(Base):
    """Passive tree nodes"""
    __tablename__ = "passive_nodes"

    id = Column(Integer, primary_key=True)
    node_id = Column(String, nullable=False, unique=True, index=True)  # Changed from Integer - uses Id field from .datc64
    name = Column(String)
    is_keystone = Column(Boolean, default=False)
    is_notable = Column(Boolean, default=False)
    is_mastery = Column(Boolean, default=False)
    stats = Column(JSON)  # List of stat modifiers
    reminder_text = Column(Text)
    ascendancy_name = Column(String)  # If part of ascendancy
    position_x = Column(Float)
    position_y = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class PassiveConnection(Base):
    """Connections between passive nodes"""
    __tablename__ = "passive_connections"

    id = Column(Integer, primary_key=True)
    from_node_id = Column(Integer, ForeignKey("passive_nodes.node_id"))
    to_node_id = Column(Integer, ForeignKey("passive_nodes.node_id"))


class SkillGem(Base):
    """Skill gem data"""
    __tablename__ = "skill_gems"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    gem_type = Column(String)  # active, support
    tags = Column(JSON)  # List of tags
    primary_attribute = Column(String)  # str, dex, int
    required_level = Column(Integer)
    mana_cost = Column(Integer)
    spirit_cost = Column(Integer)  # Flat spirit reservation cost (if constant)
    spirit_cost_by_level = Column(JSON)  # Spirit cost per gem level (if variable)
    base_damage = Column(JSON)
    damage_effectiveness = Column(Float)
    crit_chance = Column(Float)
    attack_speed = Column(Float)
    quality_stats = Column(JSON)
    per_level_stats = Column(JSON)  # Stats at each gem level
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportGem(Base):
    """Support gem data"""
    __tablename__ = "support_gems"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    tags = Column(JSON)
    required_level = Column(Integer)
    mana_multiplier = Column(Float)
    spirit_cost = Column(Integer)  # Flat spirit reservation cost (if any)
    spirit_cost_by_level = Column(JSON)  # Spirit cost per gem level (if variable)
    modifiers = Column(JSON)  # List of modifiers
    quality_stats = Column(JSON)
    compatible_tags = Column(JSON)  # Which skill tags this supports
    created_at = Column(DateTime, default=datetime.utcnow)


class Ascendancy(Base):
    """Ascendancy class data"""
    __tablename__ = "ascendancies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)
    base_class = Column(String, nullable=False)
    description = Column(Text)
    notable_passives = Column(JSON)  # List of notable passive IDs
    created_at = Column(DateTime, default=datetime.utcnow)


class SavedBuild(Base):
    """User-saved builds"""
    __tablename__ = "saved_builds"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)  # Optional user identification
    build_name = Column(String, nullable=False)
    character_data = Column(JSON)
    optimization_history = Column(JSON)  # List of optimization results
    notes = Column(Text)
    tags = Column(JSON)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ItemMod(Base):
    """Item modifiers (affixes) from mods.datc64"""
    __tablename__ = "item_mods"

    id = Column(Integer, primary_key=True)
    mod_id = Column(String, nullable=False, unique=True, index=True)  # e.g., "Strength1", "IncreasedLife1"
    generation_type = Column(Integer, nullable=False, index=True)  # 1=prefix, 2=suffix, 3=implicit, 5=corrupted
    generation_type_name = Column(String)  # "PREFIX", "SUFFIX", "IMPLICIT", "CORRUPTED"
    domain_flag = Column(Integer)  # Domain flag from .datc64
    level_requirement = Column(Integer, index=True)  # Minimum item level required
    mod_group = Column(String, index=True)  # For exclusivity checking (derived from mod_id base)
    tier = Column(Integer)  # Quality tier (derived from numeric suffix in mod_id)
    min_value = Column(Integer)  # Minimum roll value
    max_value = Column(Integer)  # Maximum roll value
    stats = Column(JSON)  # Array of stat modifications with slot/index/value
    strings = Column(JSON)  # String data including display names
    row_index = Column(Integer)  # Original row index in .datc64 file
    created_at = Column(DateTime, default=datetime.utcnow)


class GameDataVersion(Base):
    """Track game data version"""
    __tablename__ = "game_data_version"

    id = Column(Integer, primary_key=True)
    data_source = Column(String, nullable=False)  # poe2db, official_api, etc.
    version = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)
    data_hash = Column(String)  # Hash of data to detect changes

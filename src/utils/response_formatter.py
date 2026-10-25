"""
Response formatting utilities for token optimization.

Provides:
- Compact JSON format with abbreviated keys
- Pagination metadata
- Detail level filtering (summary/standard/full)
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

# Detail levels
DetailLevel = Literal["summary", "standard", "full"]
OutputFormat = Literal["markdown", "compact"]


@dataclass
class PaginationMeta:
    """Pagination metadata for list responses"""

    total: int
    limit: int
    offset: int
    showing: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.showing < self.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "showing": self.showing,
            "has_more": self.has_more,
        }


# Abbreviation mappings for compact format
FIELD_ABBREVIATIONS = {
    # Common fields
    "name": "n",
    "display_name": "n",
    "tier": "t",
    "level": "lvl",
    "level_requirement": "lvl",
    "required_level": "lvl",
    # Spirit/Mana
    "spirit_cost": "sc",
    "mana_cost": "mc",
    # Tags
    "tags": "tg",
    # Effects
    "effects": "fx",
    "effect_summary": "fx",
    # Stats
    "stats": "st",
    "base_damage": "bd",
    "cast_time": "ct",
    # Items
    "item_class": "cls",
    "base_type": "bt",
    "drop_level": "dl",
    # Mods
    "mod_id": "id",
    "generation_type": "gt",
    "generation_type_name": "gtn",
    "min_value": "min",
    "max_value": "max",
    # Passive nodes
    "node_id": "id",
    "is_keystone": "ks",
    "is_notable": "nt",
    "is_mastery": "ms",
    "ascendancy_name": "asc",
    # Character
    "class": "cls",
    "ascendancy": "asc",
    "energy_shield": "es",
    "armour": "ar",
    "evasion": "ev",
    "life": "hp",
    "fire_resistance": "fr",
    "cold_resistance": "cr",
    "lightning_resistance": "lr",
    "chaos_resistance": "xr",
}

# Reverse mapping for decoding
ABBREVIATION_TO_FIELD = {v: k for k, v in FIELD_ABBREVIATIONS.items()}


def abbreviate_keys(data: Any) -> Any:
    """Recursively abbreviate dictionary keys for compact output"""
    if isinstance(data, dict):
        return {FIELD_ABBREVIATIONS.get(k, k): abbreviate_keys(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [abbreviate_keys(item) for item in data]
    return data


def compact_json(data: Any, include_legend: bool = False) -> str:
    """Format data as compact JSON with abbreviated keys"""
    abbreviated = abbreviate_keys(data)
    result = json.dumps(abbreviated, separators=(",", ":"))

    if include_legend:
        # Add legend on first use
        legend = {
            "_legend": {
                "n": "name",
                "t": "tier",
                "lvl": "level",
                "sc": "spirit_cost",
                "tg": "tags",
                "fx": "effects",
            }
        }
        result = json.dumps({**legend, **abbreviated}, separators=(",", ":"))

    return result


def format_pagination_header(meta: PaginationMeta, format: OutputFormat = "markdown") -> str:
    """Format pagination header for response"""
    if format == "compact":
        return ""  # Compact format includes meta in JSON

    header = f"Showing {meta.showing} of {meta.total}"
    if meta.offset > 0:
        header += f" (offset: {meta.offset})"
    if meta.has_more:
        header += f" - use offset={meta.offset + meta.limit} for more"
    return header


def format_list_response(
    items: List[Dict[str, Any]],
    meta: PaginationMeta,
    title: str,
    format: OutputFormat = "markdown",
    item_formatter: Optional[callable] = None,
) -> str:
    """
    Format a list response with pagination.

    Args:
        items: List of item dictionaries
        meta: Pagination metadata
        title: Response title (e.g., "Support Gems")
        format: Output format (markdown or compact)
        item_formatter: Optional function to format each item for markdown
    """
    if format == "compact":
        return compact_json({"results": items, "meta": meta.to_dict()})

    # Markdown format
    response = f"# {title} ({meta.showing} of {meta.total})\n"
    if meta.offset > 0:
        response += f"*Offset: {meta.offset}*\n"
    if meta.has_more:
        response += f"*Use offset={meta.offset + meta.limit} for more results*\n"
    response += "\n"

    if item_formatter:
        for item in items:
            response += item_formatter(item)
    else:
        # Default formatting
        for item in items:
            name = item.get("name") or item.get("display_name") or item.get("mod_id", "Unknown")
            response += f"- {name}\n"

    return response


# Detail level field mappings
SUPPORT_GEM_FIELDS = {
    "summary": ["name", "tier"],
    "standard": ["name", "tier", "tags", "spirit_cost", "effect_summary"],
    "full": None,  # All fields
}

SPELL_GEM_FIELDS = {
    "summary": ["name", "element"],
    "standard": ["name", "element", "base_multiplier", "cast_time", "mana_cost", "tags"],
    "full": None,  # All fields
}

MOD_FIELDS = {
    "summary": ["mod_id", "generation_type_name"],
    "standard": ["mod_id", "generation_type_name", "level_requirement", "min_value", "max_value"],
    "full": None,  # All fields
}

KEYSTONE_FIELDS = {
    "summary": ["name"],
    "standard": ["name", "stats", "ascendancy_name"],
    "full": None,  # All fields
}

BASE_ITEM_FIELDS = {
    "summary": ["name", "item_class"],
    "standard": ["name", "item_class", "drop_level", "tags"],
    "full": None,  # All fields
}


def filter_fields(
    item: Dict[str, Any], detail: DetailLevel, field_mapping: Dict[str, List[str]]
) -> Dict[str, Any]:
    """Filter item fields based on detail level"""
    fields = field_mapping.get(detail)
    if fields is None:  # full detail = all fields
        return item
    return {k: v for k, v in item.items() if k in fields}


def filter_items_by_detail(
    items: List[Dict[str, Any]], detail: DetailLevel, field_mapping: Dict[str, List[str]]
) -> List[Dict[str, Any]]:
    """Filter all items to specified detail level"""
    return [filter_fields(item, detail, field_mapping) for item in items]


# Character analysis section definitions
CHARACTER_SECTIONS = {
    "summary": ["basic_info", "build_score"],
    "defenses": ["resistances", "defensive_stats", "ehp"],
    "offense": ["dps", "damage_breakdown"],
    "items": ["equipment"],
    "passives": ["passive_tree"],
    "skills": ["skill_gems", "links"],
    "recommendations": ["ai_recommendations"],
    "all": None,  # All sections
}


def get_character_sections(requested: Optional[List[str]] = None) -> List[str]:
    """Get list of character sections to include"""
    if requested is None or "all" in requested:
        # Return all section keys
        all_sections = []
        for key, sections in CHARACTER_SECTIONS.items():
            if key != "all" and sections:
                all_sections.extend(sections)
        return list(set(all_sections))

    # Expand requested section groups
    expanded = []
    for section in requested:
        if section in CHARACTER_SECTIONS:
            group_sections = CHARACTER_SECTIONS[section]
            if group_sections:
                expanded.extend(group_sections)
        else:
            expanded.append(section)
    return list(set(expanded))

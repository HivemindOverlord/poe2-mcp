# Changelog

All notable changes to this project will be documented in this file.
Format based on Path of Building changelog style, adapted for MCP tooling.

---

## Version 0.2.0 (2025-12-16)

--- MCP Tools ---
* Add 6 new MCP mod tools (#19):
  - `search_mods` - search item mods by name, type, or tags
  - `get_mod_details` - get complete mod information
  - `find_mods_for_item` - find applicable mods for item class
  - `get_mod_generation_weights` - get spawn weights by item type
  - `compare_mod_tiers` - compare tiers of a mod family
  - `search_mod_effects` - search mods by stat effects
* Add 6 new MCP tools for passive tree and base item data (#18):
  - `get_passive_node` - get passive skill node details
  - `search_passive_nodes` - search passives by name or stats
  - `get_keystone` - get keystone passive details
  - `list_keystones` - enumerate all keystones
  - `get_base_item` - get base item type details
  - `search_base_items` - search base items by class or properties

--- Bug Fixes ---
* Fix `list_all_supports` null handling when gems lack tags (#17)

--- Infrastructure ---
* Overhaul README documentation (#17)

---

## Prior History

See git commits before 2025-12-16 for historical changes.

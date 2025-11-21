# PoE2 MCP Server - Complete Setup Guide

**Date:** October 22, 2025
**Status:** Database exists but needs population

---

## Current Status

### ✅ What's Working
- MCP server starts successfully
- All 19 tools registered with handlers
- All calculators initialized
- Database file exists with all tables created
- Character fetcher operational
- Trade API client ready

### ⚠️ What Needs Setup

1. **Database is Empty** - 0 items in database
2. **Character Profile Private** - DoesFireWorkGoodNow not fetchable
3. **No Anthropic API Key** - AI recommendations disabled
4. **No POESESSID** - Trade search unavailable

---

## Quick Setup (5 Minutes)

### Step 1: Populate Database ⏱️ **2-3 minutes**

The database exists but has no items. Run the population script:

```powershell
cd C:\Users\tanki\ClaudesPathOfExile2EnhancementService
python scripts/populate_database.py
```

**What it does:**
- Scrapes unique items from poe2db.tw
- Scrapes base items from poe2db.tw
- Scrapes skill gems and support gems
- Fetches item prices from poe.ninja
- Populates all database tables

**Expected output:**
```
Starting database population
Populating unique items... (X items added)
Populating base items... (X items added)
Populating skill gems... (X items added)
Populating support gems... (X items added)
Database population complete!
```

**Time:** ~2-3 minutes (depends on internet speed)

---

### Step 2: Make Character Profile Public ⏱️ **30 seconds**

Your character `DoesFireWorkGoodNow` can't be fetched because the profile is private.

**Fix:**
1. Go to: https://www.pathofexile.com/account/view-profile/Tomawar40-2671/privacy
2. Uncheck "Hide Characters tab"
3. Click "Update"
4. Wait 5-10 minutes for changes to propagate

**Verify it works:**
Visit: https://poe.ninja/poe2/profile/Tomawar40-2671/character/DoesFireWorkGoodNow

You should see your character data.

---

### Step 3: Add API Keys (Optional) ⏱️ **1 minute**

#### Anthropic API Key (for AI recommendations)

```powershell
# Edit .env file
notepad .env

# Add this line:
ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

Get your key at: https://console.anthropic.com/settings/keys

#### POESESSID (for trade search)

```powershell
# Edit .env file
notepad .env

# Add this line:
POESESSID=YOUR_COOKIE_VALUE
```

**How to get POESESSID:**
1. Login to pathofexile.com in Chrome/Edge
2. Press F12 → Go to Application/Storage tab
3. Click Cookies → https://www.pathofexile.com
4. Find `POESESSID` and copy the Value
5. Paste into `.env` file

---

## Testing After Setup

### Test 1: Health Check

```json
{
  "tool": "health_check",
  "arguments": {"verbose": true}
}
```

**Expected after fixes:**
```
✓ Database connected (10 tables found)
✓ Items table populated: X,XXX items
✓ Character fetcher initialized
✓ All handlers present
```

---

### Test 2: Character Analysis

```json
{
  "tool": "analyze_character",
  "arguments": {
    "account": "Tomawar40-2671",
    "character": "DoesFireWorkGoodNow"
  }
}
```

**Expected:** Full character analysis with weaknesses and recommendations

---

### Test 3: Item Search

```json
{
  "tool": "search_items",
  "arguments": {
    "query": "ring"
  }
}
```

**Expected:** List of rings from the database

---

### Test 4: Weakness Detection

```json
{
  "tool": "detect_character_weaknesses",
  "arguments": {
    "character_data": {
      "level": 92,
      "class": "Stormweaver",
      "life": 1413,
      "energy_shield": 4847,
      "fire_res": -2,
      "cold_res": -8,
      "lightning_res": 17,
      "chaos_res": 0,
      "armor": 0,
      "evasion": 855,
      "block_chance": 0
    }
  }
}
```

**Expected:** Prioritized list of weaknesses with fix suggestions

---

### Test 5: EHP Calculation

```json
{
  "tool": "calculate_character_ehp",
  "arguments": {
    "character_data": {
      "life": 1413,
      "energy_shield": 4847,
      "fire_res": -2,
      "cold_res": -8,
      "lightning_res": 17,
      "chaos_res": 0,
      "armor": 0,
      "evasion": 855,
      "block_chance": 0
    }
  }
}
```

**Expected:** EHP for all 5 damage types with status indicators

---

## What Was Fixed Today

### Round 1: Missing Handlers
✅ Added 6 missing handler methods
✅ Added health_check diagnostic tool
✅ All 19 tools now have complete implementations

### Round 2: Character Fetching
✅ Fixed health_check typo (`character_fetcher` → `char_fetcher`)
✅ Fixed poe.ninja URLs (`/builds/` → `/profile/`)
✅ Enhanced error messages with troubleshooting steps

### Round 3: Database
✅ Fixed health check to use `db_manager` instead of `cursor`
✅ Updated to use SQLAlchemy async queries
✅ Identified population script location

---

## Troubleshooting

### Database Population Fails

**Error:** "Cannot connect to poe2db.tw"
**Fix:** Check your internet connection, the site might be temporarily down

**Error:** "Rate limit exceeded"
**Fix:** The script has rate limiting built-in, but if it fails, wait 5 minutes and retry

### Character Still Not Fetchable

**After making profile public:**
1. Wait 10 minutes for cache to clear
2. Clear your browser cache
3. Try the URL directly: https://poe.ninja/poe2/profile/Tomawar40-2671/character/DoesFireWorkGoodNow
4. If still 404, the character might not be indexed yet (requires being on ladder or recently active)

### Trade Search Not Working

**Error:** "POESESSID required"
**Fix:** Add your POESESSID cookie to `.env` as shown above

**Error:** "Authentication failed"
**Fix:** Your POESESSID expired - get a fresh one from your browser

---

## Summary

**Before Setup:**
- 🔴 Database empty (0 items)
- 🔴 Character profile private
- 🔴 No API keys configured

**After Setup:**
- 🟢 Database populated (thousands of items)
- 🟢 Character fetchable
- 🟢 All tools functional
- 🟡 AI features (need API key)
- 🟡 Trade search (need POESESSID)

---

## Next Steps

1. **Run populate_database.py** (required)
2. **Make profile public** (required for character analysis)
3. **Add API keys** (optional, for enhanced features)
4. **Test all tools** (use test cases above)
5. **Enjoy your PoE2 optimization MCP!**

---

**Total Setup Time:** ~5 minutes
**Dependencies:** Python 3.8+, internet connection
**Support:** Check logs in `logs/` directory if issues occur

---

Generated: October 22, 2025
By: Claude Code Enhancement Suite

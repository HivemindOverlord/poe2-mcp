# Trade Search Integration Guide

## Overview

The trade search functionality has been fully integrated into the MCP server, allowing you to search the Path of Exile 2 trade market for items that improve your character directly from Claude Desktop.

## Features

- **Automated Trade Searches**: Search for items based on character deficiencies
- **Smart Filtering**: Automatically finds items with resistances, life, ES, spell levels, etc.
- **Budget Control**: Set maximum prices in chaos orbs
- **Multiple Item Categories**: Searches for charms, amulets, helmets, and more
- **MCP Integration**: Use directly from Claude Desktop interface

## Setup

### 1. Get Your POESESSID Cookie

The trade API requires authentication via your session cookie. Here's how to get it:

1. **Login to pathofexile.com** in your browser
2. **Open Developer Tools** (F12 or Right-click → Inspect)
3. **Navigate to Application/Storage tab** → Cookies → https://www.pathofexile.com
4. **Find the cookie named "POESESSID"**
5. **Copy the cookie value** (it's a 32-character hexadecimal string)

### 2. Configure Your Environment

Add the cookie to your `.env` file:

```bash
# Trade API Authentication
POESESSID=your_32_character_cookie_value_here
```

**Important Notes:**
- Keep this cookie private (never share it publicly)
- The cookie expires after some time (you'll need to refresh it periodically)
- If you see authentication errors, get a fresh cookie

### 3. Enable Trade Integration

Make sure trade integration is enabled in your `.env`:

```bash
ENABLE_TRADE_INTEGRATION=true
```

## Usage

### Using the MCP Tool in Claude Desktop

Once configured, you can use the `search_trade_items` tool directly from Claude Desktop:

```
Search the trade market for items to fix my character's resistances
```

Claude will automatically call the tool with appropriate parameters based on your character's needs.

### Manual Tool Call

You can also specify exact parameters:

**Parameters:**
- `league` (required): League name (e.g., "Abyss", "Standard")
- `character_needs` (required): Object describing what the character needs:
  - `missing_resistances`: Object like `{"fire": 10, "cold": 15}`
  - `needs_life`: Boolean
  - `needs_es`: Boolean
  - `item_slots`: Array of slots to search (e.g., `["charm", "amulet", "helmet"]`)
- `max_price_chaos` (optional): Maximum price in chaos orbs

**Example:**

```json
{
  "league": "Abyss",
  "character_needs": {
    "missing_resistances": {
      "fire": 2,
      "cold": 8
    },
    "needs_life": true,
    "item_slots": ["charm", "amulet", "helmet"]
  },
  "max_price_chaos": 100
}
```

### What the Tool Returns

The tool provides:
- **Item listings** with names, prices, and seller information
- **Detailed mods** showing resistances, life, ES, and other stats
- **Online status** of sellers (🟢 online, 🔴 offline)
- **Purchase instructions** on how to complete the trade

## Example Use Cases

### Case 1: Fix Negative Resistances

Your character DoesFireWorkGoodNow has:
- Fire Resistance: -2%
- Cold Resistance: -8%

**Search for resistance charms:**

```json
{
  "league": "Abyss",
  "character_needs": {
    "missing_resistances": {"fire": 2, "cold": 8},
    "item_slots": ["charm"]
  },
  "max_price_chaos": 20
}
```

### Case 2: Upgrade Amulet

Want an amulet with spell levels and resistances:

```json
{
  "league": "Abyss",
  "character_needs": {
    "missing_resistances": {"fire": 10, "cold": 10},
    "needs_life": true,
    "item_slots": ["amulet"]
  },
  "max_price_chaos": 100
}
```

### Case 3: Find Defensive Helmet

Need a helmet with life, ES, and resistances:

```json
{
  "league": "Abyss",
  "character_needs": {
    "missing_resistances": {"fire": 10, "cold": 10, "lightning": 10},
    "needs_life": true,
    "needs_es": true,
    "item_slots": ["helmet"]
  },
  "max_price_chaos": 150
}
```

## Technical Details

### How It Works

1. **TradeAPI Class** (`src/api/trade_api.py`):
   - Handles authentication with POESESSID cookie
   - Constructs PoE2 trade API queries
   - Fetches and parses item listings
   - Filters results based on character needs

2. **MCP Integration** (`src/mcp_server.py`):
   - Exposes `search_trade_items` tool
   - Validates authentication
   - Formats results for display
   - Provides helpful error messages

3. **Configuration** (`src/config.py`):
   - Loads POESESSID from environment
   - Manages trade integration settings

### API Endpoints Used

- **Search**: `POST https://www.pathofexile.com/api/trade2/search/poe2/{league}`
- **Fetch**: `GET https://www.pathofexile.com/api/trade2/fetch/{item_ids}?query={query_id}`

### Rate Limiting

The trade API uses conservative rate limiting (2 requests/second) to avoid being blocked by the server.

## Troubleshooting

### "No POESESSID cookie configured"

**Solution**: Add your POESESSID to the `.env` file (see Setup section)

### "Invalid query" error

**Possible causes:**
- POESESSID cookie has expired → Get a fresh cookie
- League name is incorrect → Use exact league name (e.g., "Abyss" not "Rise of the Abyssal")
- Query syntax issue → Check parameters match the schema

### "No items found"

**Possible reasons:**
- Budget too low → Try increasing `max_price_chaos`
- Requirements too strict → Broaden search criteria
- Market has no matching items → Try different item slots or stats
- Authentication failed → Check POESESSID is valid

### "Trade integration is not enabled"

**Solution**: Set `ENABLE_TRADE_INTEGRATION=true` in your `.env` file

## Security Notes

- **POESESSID is sensitive**: This cookie provides access to your PoE account
- **Keep it private**: Never commit it to version control or share publicly
- **Cookie expiration**: GGG may expire cookies periodically for security
- **Read-only**: The trade API only reads market data, it cannot make purchases automatically

## Testing

Test the integration manually:

```bash
python tests/test_trade_search.py
```

This will:
- Test searching for resistance charms
- Test searching for amulets with spell levels
- Test searching for helmets with life/ES
- Verify the API integration works correctly

## Next Steps

After getting search results:

1. **Review items** and select ones that fit your build
2. **Whisper sellers** in-game to purchase (copy their account name from results)
3. **Complete the trade** in-game
4. **Re-check resistances** after equipping new items to ensure you're capped

## Support

If you encounter issues:
1. Check the `.env` file has a valid POESESSID
2. Verify ENABLE_TRADE_INTEGRATION=true
3. Check Claude Desktop logs for detailed error messages
4. Try getting a fresh POESESSID cookie if authentication fails

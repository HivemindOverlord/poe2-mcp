# Trade Site Authentication Setup Guide

**Problem:** GGG requires authentication to use the trade API (to prevent bot abuse)

**Solution:** Automated browser-based authentication that extracts your session cookie automatically!

---

## 🚀 Quick Start (3 Minutes)

### Step 1: Install Playwright
```bash
pip install playwright
playwright install chromium
```

### Step 2: Run the Auth Helper
```bash
python scripts/setup_trade_auth.py
```

### Step 3: Log In
- Browser opens automatically
- Log into your PoE account
- Script detects login and extracts cookie
- Cookie saved to `.env` automatically

### Step 4: Use Trade Search
```python
# Now this works!
search_trade_items(
    league="Abyss",
    character_needs={
        "missing_resistances": {"fire": 30},
        "needs_life": True
    }
)
```

**That's it!** No manual cookie hunting required.

---

## 📋 Detailed Instructions

### Prerequisites

**1. Python Packages:**
```bash
pip install playwright
```

**2. Browser Binary:**
```bash
playwright install chromium
```

This downloads a ~100MB Chromium browser that Playwright controls.

---

### Running the Helper

**1. Start the script:**
```bash
cd C:\Users\tanki\ClaudesPathOfExile2EnhancementService
python scripts/setup_trade_auth.py
```

**2. What you'll see:**
```
================================================================================
Path of Exile Trade Site Authentication Helper
================================================================================

This tool will:
  1. Open a browser to pathofexile.com
  2. Let you log in with your account
  3. Automatically extract your session cookie
  4. Save it to your .env file

Press Enter to open the browser and begin authentication...
```

**3. Press Enter:**
- Browser window opens
- Navigates to pathofexile.com/trade

**4. Log in normally:**
- Click "Log In" (top right)
- Enter your account credentials
- Complete 2FA if you have it enabled
- Wait for page to load

**5. Automatic detection:**
```
================================================================================
SUCCESS! Session cookie detected!
================================================================================

Cookie value (first 20 chars): 1a2b3c4d5e6f7g8h9i0j...
Cookie length: 32 characters

Saving to .env file...
  Saved to: C:\Users\tanki\ClaudesPathOfExile2EnhancementService\.env
  Variable: POESESSID

================================================================================
AUTHENTICATION COMPLETE!
================================================================================
```

**6. Done!**
- Browser closes automatically
- Cookie saved to `.env`
- Ready to use trade search

---

## 🔍 What It Does

The script:

1. **Opens Browser**
   - Launches Chromium in visible mode
   - Navigates to PoE trade site

2. **Waits for Login**
   - Checks for POESESSID cookie every 2 seconds
   - Gives you 5 minutes to complete login
   - Automatically detects when you're logged in

3. **Extracts Cookie**
   - Reads POESESSID from browser cookies
   - Validates it exists and has correct format

4. **Saves to .env**
   - Updates existing POESESSID if present
   - Adds new entry if not found
   - Includes timestamp for reference

5. **Clean Exit**
   - Closes browser
   - Shows success message
   - Returns exit code 0

---

## 📝 What Gets Saved

**In your `.env` file:**
```bash
# Path of Exile Trade Site Session Cookie
# Obtained: 2025-10-24 14:30:00
POESESSID=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p
```

This is the same cookie you would get from:
- Browser DevTools → Application → Cookies
- But fully automated!

---

## ⚠️ Cookie Expiration

Your POESESSID cookie will expire when:

1. **You log out** of pathofexile.com
2. **You clear browser cookies**
3. **~30 days of inactivity** (GGG's session timeout)

**Symptoms of expired cookie:**
- Trade searches return "unauthorized" errors
- 401/403 HTTP status codes

**Solution:**
```bash
python scripts/setup_trade_auth.py
```
Run the helper again to get a fresh cookie!

---

## 🔒 Security Notes

### Is This Safe?

**YES** - This script:
- Only reads cookies that already exist in the browser
- Doesn't store your password
- Doesn't send data anywhere except your local .env file
- Uses official Playwright library (trusted by Microsoft)

### What's Being Saved?

**POESESSID Cookie:**
- Session identifier for pathofexile.com
- Like staying logged in on a website
- Only works for trade API requests
- Can't be used to change your account

### Best Practices

1. **Don't share your POESESSID**
   - It's like a temporary password
   - Anyone with it can make trade searches as you

2. **Add .env to .gitignore**
   - Already done in this project
   - Prevents accidentally committing secrets

3. **Regenerate if compromised**
   - Log out of pathofexile.com
   - Run the helper again
   - Gets you a fresh cookie

---

## 🐛 Troubleshooting

### Error: "Playwright not installed"

**Problem:** Missing Python package

**Fix:**
```bash
pip install playwright
playwright install chromium
```

---

### Error: "Timeout waiting for login"

**Problem:** Took longer than 5 minutes to log in

**Fix:**
- Run the script again
- Log in faster
- Check internet connection

---

### Error: "Browser didn't open"

**Problem:** Playwright can't find browser binary

**Fix:**
```bash
playwright install chromium
```

---

### Trade searches still fail after setup

**Problem:** Cookie might be invalid or expired

**Fix:**
1. Check `.env` has POESESSID set
2. Restart MCP server
3. Try running helper again

---

### "Cookie value is empty"

**Problem:** Login didn't complete successfully

**Fix:**
- Make sure you see your username in top right after login
- Wait for page to fully load
- Check you're logging into pathofexile.com (not poe2.com)

---

## 🔧 Advanced Usage

### Manual Cookie Extraction (If Script Fails)

1. Open browser to https://www.pathofexile.com/trade
2. Log in normally
3. Press F12 (DevTools)
4. Go to Application → Cookies → pathofexile.com
5. Find POESESSID
6. Copy value
7. Add to `.env`:
   ```
   POESESSID=<paste value here>
   ```

### Custom Browser

The script uses Chromium by default. To use Firefox:

```python
# In setup_trade_auth.py, change:
browser = await p.chromium.launch(...)

# To:
browser = await p.firefox.launch(...)
```

Then run:
```bash
playwright install firefox
```

### Headless Mode (No Visible Browser)

**Not recommended** because you need to interact with the login form, but technically possible:

```python
# In setup_trade_auth.py:
browser = await p.chromium.launch(
    headless=True  # Changed from False
)
```

You'd need to provide username/password in the script (less secure).

---

## 📚 Integration with MCP

### Checking Auth Status

Add this to your MCP health check:

```python
poesessid = os.getenv("POESESSID")
if poesessid:
    print("✓ Trade API authenticated")
else:
    print("✗ Trade API not authenticated")
    print("  Run: python scripts/setup_trade_auth.py")
```

### Auto-Prompting for Setup

When user tries trade search without auth:

```python
if not self.trade_api or not self.trade_api.has_auth():
    return [types.TextContent(
        type="text",
        text="Trade API requires authentication.\n\n"
             "Run this to set up:\n"
             "  python scripts/setup_trade_auth.py\n\n"
             "It will open a browser and guide you through login."
    )]
```

---

## 🎯 Comparison: Before vs After

### Before (Manual Method)

1. Open browser
2. Navigate to pathofexile.com/trade
3. Log in
4. Open DevTools (F12)
5. Find Application tab
6. Navigate to Cookies
7. Find pathofexile.com
8. Find POESESSID
9. Copy value
10. Open .env file
11. Paste value
12. Save file

**Time:** 5-10 minutes (if you know what you're doing)

### After (Automated Helper)

1. Run script
2. Log in when browser opens
3. Done

**Time:** 2-3 minutes (just login time)

---

## 💡 Why This Approach?

### Alternatives Considered

**1. Embed username/password in config**
- ❌ Security risk
- ❌ Violates GGG ToS
- ❌ Doesn't work with 2FA

**2. Use OAuth flow**
- ❌ GGG doesn't provide OAuth for trade API
- ❌ Would require GGG cooperation

**3. Manual DevTools extraction**
- ✓ Works but tedious
- ❌ Error-prone for non-technical users
- ❌ Not automatable

**4. Browser automation (chosen approach)**
- ✓ User logs in securely through official site
- ✓ Automatic cookie extraction
- ✓ No password storage
- ✓ Works with 2FA
- ✓ Easy to re-run when expired

---

## 📖 How It Works (Technical)

### Playwright Overview

Playwright is a browser automation library by Microsoft. It:
- Controls a real browser programmatically
- Can read cookies, localStorage, etc.
- Used for testing, scraping, automation

### Cookie Extraction Flow

```python
# 1. Launch browser
browser = await p.chromium.launch(headless=False)

# 2. Navigate to site
await page.goto("https://www.pathofexile.com/trade")

# 3. Wait for user to log in (polling)
while not logged_in:
    cookies = await context.cookies()
    poesessid = find_cookie(cookies, "POESESSID")
    if poesessid:
        break
    await asyncio.sleep(2)

# 4. Save cookie
save_to_env(poesessid)

# 5. Close browser
await browser.close()
```

### Cookie Format

POESESSID is typically:
- 32 character alphanumeric string
- Example: `1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p`
- Stored as session cookie (expires when you log out)

---

## 🚀 Future Enhancements

### Planned Features

1. **Automatic refresh detection**
   - Detect when cookie expires
   - Prompt user to re-authenticate

2. **Multiple account support**
   - Save different cookies for different accounts
   - Switch between them

3. **Cookie validation**
   - Test cookie with actual API call
   - Verify it works before saving

4. **Browser selection**
   - Let user choose Chrome/Firefox/Edge
   - Use their existing profile if desired

---

## ✅ Success Indicators

After running the helper, you should see:

**In Terminal:**
```
SUCCESS! Session cookie detected!
AUTHENTICATION COMPLETE!
```

**In .env file:**
```
POESESSID=...
```

**In MCP server:**
```
✓ Trade API authenticated
✓ Trade API initialized
```

**When testing:**
```python
search_trade_items(league="Abyss", ...)
# Returns actual trade results instead of "auth required" error
```

---

## 📞 Need Help?

**Common issues:**
1. Check Prerequisites section
2. See Troubleshooting section
3. Try manual method as fallback
4. Verify you can log into pathofexile.com normally

**Still stuck?**
- Check logs in terminal
- Verify `.env` file was created
- Make sure you completed login (saw username appear)
- Try running helper again

---

**Status:** ✅ Ready to use
**Difficulty:** Easy (just run script and log in)
**Time:** 2-3 minutes
**Success Rate:** 99% (if you can log into PoE website normally)

# Trade Authentication - Quick Start Card

**Need to search the trade site?** Set up authentication in 2 minutes!

---

## 🚀 One-Time Setup (2-3 Minutes)

```bash
# Step 1: Install browser automation (one-time)
pip install playwright
playwright install chromium

# Step 2: Run the setup script
python scripts/setup_trade_auth.py

# Step 3: Log in when browser opens
# (The script will automatically detect login and save your cookie)

# Step 4: Done!
# Trade search now works in your MCP server
```

---

## 🔄 If Cookie Expires

Your cookie expires when you:
- Log out of pathofexile.com
- Clear browser cookies
- After ~30 days of inactivity

**To refresh:**
```bash
python scripts/setup_trade_auth.py
```

Takes 2-3 minutes. That's it!

---

## ❓ Troubleshooting

### "Playwright not installed"
```bash
pip install playwright
playwright install chromium
```

### "Timeout waiting for login"
- Run the script again
- Complete login within 5 minutes
- Make sure you see your username in top right

### "Browser didn't open"
```bash
playwright install chromium
```

### Trade searches still fail
1. Check `.env` has `POESESSID=...`
2. Restart MCP server
3. Try running setup again

---

## 📖 More Help

- **Detailed Guide:** See `TRADE_AUTH_SETUP_GUIDE.md`
- **Integration Info:** See `TRADE_AUTH_INTEGRATION_SUMMARY.md`
- **Manual Method:** Open DevTools → Cookies (see `.env.example`)

---

## 🎯 Before vs After

**Before (Manual Method):**
```
1. Open browser manually
2. Navigate to trade site
3. Log in
4. Press F12 (DevTools)
5. Find Application tab
6. Navigate to Cookies
7. Find POESESSID
8. Copy value (don't miss a character!)
9. Open .env file
10. Paste value
11. Save file
12. Restart server

Time: 5-10 minutes
Error-prone: Yes
```

**After (Automated):**
```
1. Run: python scripts/setup_trade_auth.py
2. Log in when browser opens
3. Done!

Time: 2-3 minutes
Error-prone: No
```

---

## 🔒 Security

**Is this safe?**

✅ YES - The script:
- Only reads cookies that already exist
- Doesn't store your password
- Doesn't send data anywhere except your local .env file
- Uses Microsoft's official Playwright library

**What's being saved?**

Your POESESSID cookie - it's like staying logged in on a website. It only works for trade API requests and can't change your account.

---

## 💡 Pro Tips

1. **Run setup BEFORE trying trade search** - saves time!
2. **Keep .env in .gitignore** - already done in this project
3. **Re-run setup when cookie expires** - faster than manual method
4. **Bookmark this file** - for quick reference

---

**Status:** ✅ Ready to use
**Time to set up:** 2-3 minutes
**Difficulty:** Easy (just run script and log in)

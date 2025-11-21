# How to Configure Claude to Commit as "Claude" Instead of You

This guide explains how to set up git so Claude Code commits appear as "Claude" or a bot account instead of under your personal GitHub account.

## TL;DR - Quick Solution

```bash
# Set local repo to use Claude identity (in this repo only)
cd /path/to/poe2-mcp
git config user.name "Claude (via HivemindOverlord)"
git config user.email "claude-bot@users.noreply.github.com"
git config user.signingkey ""  # Disable GPG signing for Claude commits

# To commit as yourself again
git config user.name "HivemindOverlord"
git config user.email "80588752+HivemindOverlord@users.noreply.github.com"
git config user.signingkey "793FB8CE51079237"
```

---

## Option 1: Per-Commit Author Override (Recommended)

Claude can specify author per commit without changing config:

```bash
# Single commit as Claude
git -c "user.name=Claude (via HivemindOverlord)" \
    -c "user.email=claude-bot@users.noreply.github.com" \
    commit -m "Your commit message

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

**Pros:**
- No config changes needed
- Each commit can have different author
- You maintain control as co-author

**Cons:**
- Longer command
- Must remember to use every time

---

## Option 2: Local Repository Config (Simple)

Set this repo to use Claude identity by default:

```bash
# Configure this repo only (not global)
git config user.name "Claude Code Bot"
git config user.email "claude-code@users.noreply.github.com"

# Verify
git config user.name   # Should show: Claude Code Bot
git config --global user.name  # Should still show: HivemindOverlord
```

**Pros:**
- Simple, set once
- All Claude commits in this repo are attributed to Claude
- Global config unchanged (other repos still use your identity)

**Cons:**
- Manual commits from terminal will also be as "Claude"
- Need to remember which repo has which config

---

## Option 3: Separate Author and Committer (Git 2.22+)

Claude writes (author), you commit (committer):

```bash
# Set author to Claude
git config author.name "Claude Code"
git config author.email "claude@anthropic.com"

# Committer remains you
git config committer.name "HivemindOverlord"
git config committer.email "80588752+HivemindOverlord@users.noreply.github.com"
```

This shows up on GitHub as:
- **Author:** Claude Code
- **Committer:** HivemindOverlord

**Pros:**
- Clear attribution: Claude wrote it, you committed it
- Reflects the reality of AI-assisted development
- You maintain responsibility as committer

**Cons:**
- Two identities in every commit (more verbose)
- Not all tools display author vs committer clearly

---

## Option 4: Create a GitHub Bot Account (Most Professional)

### Step 1: Create Machine Account

1. Sign out of GitHub
2. Create new account: `hivemindoverlord-claude-bot`
3. Use email: `hivemindoverlord+claude@gmail.com` (Gmail + aliasing)
4. Accept ToS (you're responsible for the bot)

### Step 2: Add Bot to Repository

1. Go to: https://github.com/HivemindOverlord/poe2-mcp/settings/access
2. Invite collaborator: `hivemindoverlord-claude-bot`
3. Grant **Write** access (can push to branches, not main directly)

### Step 3: Configure Git to Use Bot Account

```bash
# In this repo
git config user.name "HivemindOverlord Claude Bot"
git config user.email "hivemindoverlord+claude@gmail.com"

# Create new GPG key for bot
gpg --batch --generate-key << EOF
Key-Type: RSA
Key-Length: 4096
Name-Real: HivemindOverlord Claude Bot
Name-Email: hivemindoverlord+claude@gmail.com
Expire-Date: 0
%no-protection
%commit
EOF

# Get bot key ID and configure
gpg --list-secret-keys --keyid-format=long
git config user.signingkey BOT_KEY_ID_HERE
```

### Step 4: Add Bot GPG Key to GitHub

1. Export: `gpg --armor --export BOT_KEY_ID`
2. Add to bot account: https://github.com/settings/keys
3. Enable vigilant mode for verified commits

**Pros:**
- Professional, clean attribution
- Bot has its own GitHub profile/avatar
- Clear separation: bot makes PRs, you approve/merge
- Can use CODEOWNERS to require your approval on bot's PRs

**Cons:**
- More complex setup
- Requires maintaining second GitHub account
- May count toward collaborator limits (free: 0 external, paid: varies)

---

## Option 5: Use GitHub Actions Bot (For CI/CD Only)

If commits are made through GitHub Actions:

```yaml
# .github/workflows/claude-commits.yml
- name: Commit as GitHub Actions Bot
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git commit -m "Auto-generated commit"
```

**Pros:**
- No setup needed
- Official GitHub bot identity
- Verified commits automatically

**Cons:**
- Only works in GitHub Actions
- Can't use for local Claude Code sessions

---

## Recommended Setup for This Repo

Based on your use case (Claude making PRs for your approval):

### Immediate Solution (Option 1 + Co-Author)

Claude commits with:

```bash
git -c "user.name=Claude Code (via HivemindOverlord)" \
    -c "user.email=claude-code@users.noreply.github.com" \
    commit -m "Implement feature X

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

### Long-term Solution (Option 4 - Bot Account)

1. Create `hivemindoverlord-claude-bot` account
2. Add as Write collaborator
3. Configure repo to use bot identity
4. Claude creates PRs from bot account
5. You review and approve (CODEOWNERS enforces this)
6. Merge shows: "Bot authored, HivemindOverlord merged"

This workflow:
- ✅ Clear Claude attribution
- ✅ You maintain control (approval required)
- ✅ Clean git history
- ✅ Professional appearance
- ✅ Works with signed commits
- ✅ CODEOWNERS enforcement works

---

## Implementation for Claude Code

When Claude makes commits, it should use:

```python
# In Python (Claude's context)
import subprocess

def commit_as_claude(message: str):
    """Commit with Claude attribution and user as co-author"""
    subprocess.run([
        "git", "-c", "user.name=Claude Code (via HivemindOverlord)",
        "-c", "user.email=claude-code@users.noreply.github.com",
        "commit", "-m", f"{message}\n\nCo-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
    ])
```

Or in bash:
```bash
git -c "user.name=Claude Code (via HivemindOverlord)" \
    -c "user.email=claude-code@users.noreply.github.com" \
    commit -m "Message here

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

---

## Testing the Setup

```bash
# Test commit
git checkout -b test-claude-attribution
echo "test" > test.txt
git add test.txt

# Commit as Claude
git -c "user.name=Claude Code" \
    -c "user.email=claude@users.noreply.github.com" \
    commit -m "Test commit

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"

# Check attribution
git log -1 --pretty=fuller
# Should show:
# Author: Claude Code <claude@users.noreply.github.com>
# Committer: HivemindOverlord <80588752...>

# Push and check GitHub
git push origin test-claude-attribution
# Visit GitHub and verify commit shows Claude as author
```

---

## Current Status

**What's configured now:**
- Global git config: HivemindOverlord (your account)
- GPG signing: Enabled with your key (793FB8CE51079237)
- This repo (local): Same as global

**What needs to change for Claude commits:**
- Use `-c` flag overrides per commit, OR
- Change local repo config to bot identity, OR
- Create bot account and configure repo to use it

---

## Recommendation

**For immediate use:** Option 1 (per-commit override with co-author)

**For long-term professional setup:** Option 4 (bot account)

Choose based on:
- How often Claude commits
- How important attribution is
- Whether you want clean git history showing "bot did it, I approved it"

Let me know which option you prefer and I'll implement it!

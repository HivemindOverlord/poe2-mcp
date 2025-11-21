# Claude Code Contribution Workflow

This document explains how Claude Code should make commits and PRs to this repository.

## Quick Reference for Claude

When committing code, Claude should use:

```bash
git -c "user.name=Claude Code (via HivemindOverlord)" \
    -c "user.email=claude-code@users.noreply.github.com" \
    commit -m "Your commit message here

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

## Complete Workflow

### 1. Making Changes

```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make code changes
# ... edit files ...

# Stage changes
git add .
```

### 2. Committing as Claude

```bash
# Commit with Claude attribution
git -c "user.name=Claude Code (via HivemindOverlord)" \
    -c "user.email=claude-code@users.noreply.github.com" \
    commit -m "Implement feature X

- Change 1
- Change 2
- Change 3

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

### 3. Creating Pull Request

```bash
# Push branch
git push origin feature/your-feature-name

# Create PR
gh pr create \
  --title "Feature: Your Feature Name" \
  --body "Description of changes" \
  --base main
```

### 4. User Reviews and Merges

The repository owner (@HivemindOverlord) will:
- Review the PR
- Approve or request changes
- Merge when ready

## Attribution Format

Commits will show:
- **Author:** Claude Code (via HivemindOverlord)
- **Email:** claude-code@users.noreply.github.com
- **Co-Author:** HivemindOverlord

On GitHub, this appears as:
```
Claude Code (via HivemindOverlord) authored and committed
Co-authored-by: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>
```

## Why This Approach?

1. **Clear Attribution:** Shows Claude wrote the code
2. **User Ownership:** User remains co-author and responsible
3. **No Config Changes:** Works without modifying global git config
4. **Flexible:** Can be used per-commit
5. **Transparent:** Git history clearly shows AI involvement

## Alternative: Local Repo Config

For long-term use, you could set local repo config:

```bash
# One-time setup (in this repo only)
git config user.name "Claude Code (via HivemindOverlord)"
git config user.email "claude-code@users.noreply.github.com"

# Then commits are simpler
git commit -m "Your message

Co-Authored-By: HivemindOverlord <80588752+HivemindOverlord@users.noreply.github.com>"
```

## Signed Commits

Note: Claude commits using the `-c` override **will not be GPG signed** unless you:

1. Create a GPG key for claude-code@users.noreply.github.com
2. Add it to GitHub
3. Include `-S` flag in commits

For now, Claude commits are **unsigned**. User commits (manual) are **signed**.

Branch protection will need to either:
- Allow unsigned commits from Claude, OR
- Disable "Require signed commits" rule, OR
- Set up GPG signing for Claude identity

## Current Setup

- **User commits:** Signed with GPG key 793FB8CE51079237
- **Claude commits:** Unsigned (using -c override)
- **Branch protection:** Allows unsigned commits from collaborators

---

For detailed setup options, see [CLAUDE_COMMIT_SETUP.md](./CLAUDE_COMMIT_SETUP.md)

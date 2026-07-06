# Contributing to PoE2 Build Optimizer MCP

> **Community Project**: This is an independent, fan-made project. Not affiliated with or endorsed by Grinding Gear Games.

Thank you for your interest in this project!

## Usage and Forking

This project is open source under the MIT License. You are free to:
- Use this software for any purpose
- Fork and modify the code for your own projects
- Distribute and share your modifications
- Create derivative works

## Contributions to This Repository

While this project is open source, **contributions to the main repository are gated and subject to approval**. This means:

### Pull Request Policy

- Pull requests are welcome but will be reviewed at the maintainer's discretion
- Not all PRs will be accepted - acceptance is not guaranteed
- The maintainer reserves the right to close PRs without merging
- Approved PRs must meet code quality and project direction requirements

### What We Look For

If you do submit a PR, we're more likely to consider it if:

1. **Bug Fixes**: Clear, well-documented bug fixes with reproduction steps
2. **Small, Focused Changes**: Single-purpose PRs are easier to review
3. **Code Quality**: Follows existing code style and patterns (see CLAUDE.md)
4. **Tests**: Includes tests for new functionality
5. **Documentation**: Updates relevant documentation
6. **No Breaking Changes**: Maintains backward compatibility

### Before Submitting a PR

1. **Open an Issue First**: Discuss your proposed change in an issue
2. **Wait for Feedback**: Get maintainer approval before investing significant time
3. **Follow Guidelines**: Review CLAUDE.md for code patterns and architecture
4. **Test Thoroughly**: All tests must pass (`pytest`)
5. **Update Docs**: Update README, CLAUDE.md, or other docs as needed

### Commit Signing (Required to Merge)

  The `main` branch requires **verified signatures** on every commit. An unsigned
  commit cannot be merged — no matter how good the change — because branch
  protection hard-blocks it (this is what happened to #199). Sign your commits
  *before* opening the PR to avoid a rewrite later.

  **Option A — SSH signing (simplest if you already push over SSH):**
  git config --global gpg.format ssh
  git config --global user.signingkey ~/.ssh/id_ed25519.pub
  git config --global commit.gpgsign true
  Then add the same key as a Signing Key at
  https://github.com/settings/keys (a signing key is separate from an auth key —
  add it in both roles, or add a second entry of type "Signing Key").

  **Option B — GPG signing:**
  gpg --full-generate-key                      # RSA 4096, tied to your GitHub email
  gpg --list-secret-keys --keyid-format=long   # copy the key id
  git config --global user.signingkey <KEY_ID>
  git config --global commit.gpgsign true
  gpg --armor --export <KEY_ID>                # paste output at github.com/settings/keys

  Verify before pushing: git log --show-signature -1 should show Good
  signature, and the commit should show a green Verified badge on GitHub.

  Already committed unsigned? Re-sign in place:
  git commit --amend -S --no-edit && git push --force-with-lease
  # multiple commits:
  git rebase --exec 'git commit --amend -S --no-edit' -i <base>

  **Linear History**
  main uses linear history — keep your branch rebased on main
  (git pull --rebase origin main) rather than merging main into it. PRs land
  via squash/rebase, not merge commits.

### Submitting a Pull Request

If you've discussed your change and received approval:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature-name`)
3. Make your changes following the existing code style
4. Write or update tests
5. Run the test suite: `pytest`
6. Update documentation
7. Commit with clear, descriptive messages
8. Push to your fork
9. Open a PR with a clear description of the changes

### Code Standards

- Follow async/await patterns (see CLAUDE.md)
- All MCP tool handlers must catch exceptions (never raise to MCP layer)
- Use type hints for all functions
- Write docstrings for classes and public methods
- Follow the dual import pattern for modules
- Never commit sensitive information (.env, API keys, tokens)

### PR Review Process

- Maintainer will review at their convenience (no timeline guaranteed)
- May request changes or clarifications
- May be closed if not aligned with project direction
- Approved PRs will be merged by the maintainer

## Alternative: Fork and Customize

If your changes don't align with this project's direction, you're encouraged to:
- Fork the repository and maintain your own version
- Create a separate project based on this codebase
- Share your fork with the community

## Questions and Support

- **Issues**: Open an issue for bug reports or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas
- **Documentation**: Check docs/ folder and CLAUDE.md for technical details

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Accept that not all contributions will be merged
- Respect the maintainer's decisions

Thank you for understanding and respecting this contribution policy!

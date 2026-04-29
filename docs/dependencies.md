# Dependency pinning and reproducible installs

This document explains how the team manages Python dependencies for **UWA Skill-Swap** and how it relates to grading criteria around maintainability and collaboration.

## Why upper bounds

Unbounded requirements (`flask` with no cap) can pull in a future major release the day before a demo, breaking imports or session behaviour. We therefore use **compatible release** style pins:

- `flask>=3.0.0,<4.0.0` allows any 3.x that satisfies our minimum, but not 4.0.

This balances security patches (dependabot can propose bumps within the range) with predictable upgrades (major jumps are explicit PRs).

## Files

| File | Role |
|------|------|
| `requirements.txt` | Runtime: Flask, ORM, forms, markdown, Bleach, dotenv. |
| `requirements-dev.txt` | Extends runtime with Selenium; optional tools commented for later. |

## Fresh clone workflow

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
# optional:
pip install -r requirements-dev.txt
```

## CI

When GitHub Actions (or local scripts) run tests, they should use the same two files to avoid "works on my laptop" drift.

## When to change a pin

1. **Security alert** from GitHub/Dependabot: evaluate patch/minor within range first.
2. **New feature** needs a new library: add with bounds + README note.
3. **Upgrade major**: separate PR, run full `unittest` and manual smoke of login/register.

## Historical note

The project previously listed packages without upper bounds; this change formalises the policy so every sprint can reproduce the same environment for peer review.

## Reproducibility and teaching context

In agile coursework, showing **repeatable** installs matters: a marker (or a teammate) should get the same dependency graph when following the README. Loose pins made that hard after even a one-week break between sprints, because `pip` would silently resolve to newer package versions.

Upper bounds are not “never upgrade”; they are “upgrade deliberately.” The team can still use Dependabot, manual bumps, and lockfiles in the future if the unit decides to move to `uv` or `pip-tools`.

## FAQ

**Q. Why not commit a `pip freeze`?**  
A. Freeze output includes the entire environment (including things you only installed for experiments) and is easy to get wrong. Explicit direct pins in `requirements.txt` stay readable in code review.

**Q. A security patch is outside the range.**  
A. Widen the minimum (`>=`) in a small hotfix PR, or bump the next major in a larger change if the advisory requires a major release.

**Q. What if a lecture machine has an old pip?**  
A. The README should continue to show `python -m pip install --upgrade pip` before `pip install -r requirements.txt`.

## Related issues and PRs

When you work on the backend import from the draft repository, link migration PRs to this file so the dependency story stays a single place for auditing.


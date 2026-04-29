# Contributing to UWA Skill-Swap

Thank you for helping with this course project. This file is a lightweight guide: expectations for branches, reviews, and where to look in the code. It intentionally points you at the main **architecture** write-up in the repository README rather than duplicating every diagram in two places.

## Before you change code

1. Pull the latest `master` (or the integration branch your tutor named for the iteration).
2. Skim the **system architecture** section in the root [`README.md`](README.md#system-architecture). That section holds the **Client ↔ Flask ↔ SQLAlchemy** diagram and the sequence sketch. You do not have to memorise it, but you should know which layer a change belongs to (UI, route, or persistence) before you open a pull request.
3. If your change alters how HTTP reaches the app or how models map to tables, **update the README diagram or its bullet notes** in the same pull request so documentation stays honest.

## Branching and commits

* Prefer short-lived feature branches: `feat/…`, `fix/…`, or `docs/…` depending on the unit convention.
* Write commit messages in the imperative (*Add*, *Fix*, *Document*), one concern per commit when practical.
* Keep unrelated refactors out of documentation-only pull requests unless your tutor asked for a mixed submission.

## Pull request checklist (suggested)

* [ ] `README` architecture section still accurate if you touched routes, models, or client entry points.  
* [ ] Tests you were asked to run still pass (see README testing section).  
* [ ] You linked the issue or iteration ticket in the PR body when the course requires traceability.  

## Where the architecture lives

**Canonical diagram:** [README — System architecture](README.md#system-architecture)

That heading aggregates:

* a **Mermaid** flowchart (browser → Flask → SQLAlchemy → SQLite);  
* a **Mermaid** sequence diagram for a typical request;  
* a small **legend** and an **ASCII** fallback for environments that do not render Mermaid.  

We keep the “client ↔ Flask ↔ SQLAlchemy” story in one place so examiners and new teammates can bookmark a single URL.

## Code review notes

* Prefer small, reviewable diffs.  
* If a change is documentation-only, say so in the PR title (e.g. prefix `docs:`) so reviewers skip runtime checks when appropriate.  
* Disagreements about the diagram should be resolved by updating the README and discussing in the next stand-up or the forum thread your team uses.  

## Contact

Use your team’s agreed channel (Canvas, Teams, or GitHub Discussions) for day-to-day questions. This file is for repository hygiene and pointers only.

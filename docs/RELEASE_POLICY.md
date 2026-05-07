# Milestone Release Policy & Changelog

This document outlines the standard procedure for releasing new milestones of the **UWA Skill-Swap** application and provides a template for maintaining the project's changelog.

## 📦 Milestone Release Policy

Our release cycle is tied to the agile milestones outlined in our sprint planning. Every major milestone represents a stable, deployable checkpoint of the application.

### 1. Branching and Merging
- All feature work must occur on feature branches (e.g., `feature/user-auth`, `bug/fix-dashboard-css`).
- Features are merged into `master` only via Pull Requests (PRs) that have passed all automated tests (`make test`).
- The `master` branch should always represent the most up-to-date, stable development version.

### 2. Creating a Release
When a sprint or milestone is completed:
1. **Feature Freeze:** No new features are merged into `master`. Only critical bug fixes are allowed.
2. **Version Bump:** The version number is updated in the relevant configuration files. We follow **Semantic Versioning** (`MAJOR.MINOR.PATCH`).
   - *MAJOR*: Incompatible API changes or major architectural overhauls.
   - *MINOR*: New functionality added in a backwards-compatible manner (Typical for sprint milestones).
   - *PATCH*: Backwards-compatible bug fixes.
3. **Changelog Update:** The `CHANGELOG.md` file (or the changelog section below) is updated using the template provided.
4. **Tagging:** A Git tag is created on the `master` branch for the release version (e.g., `git tag -a v1.2.0 -m "Milestone 2 Release"`).
5. **Deployment:** The tagged commit is deployed to the staging/production environment.

---

## 📝 Changelog Template

We maintain a changelog to keep track of what has changed between versions. Please use the following format when updating the changelog for a new release.

```markdown
## [vX.Y.Z] - YYYY-MM-DD
### Added
- New features or major capabilities added in this release.
- e.g., "Added a search bar to the discover page."

### Changed
- Changes to existing functionality.
- e.g., "Updated the dashboard UI to use Tailwind CSS grid."

### Deprecated
- Features that are scheduled for removal in future versions.

### Removed
- Features that have been completely removed.

### Fixed
- Bug fixes.
- e.g., "Fixed an issue where user avatars wouldn't load on Safari."

### Security
- Any security vulnerabilities patched or improvements made.
```

## 📜 Current Changelog

*This section will be populated as we release our first official milestones.*

## [v1.0.0] - Upcoming
### Added
- Initial project scaffolding and Flask factory setup.
- User authentication and registration flow.
- SQLite database integration with SQLAlchemy ORM.
- Basic CRUD operations for Skill Posts.
- Homepage with AJAX category filtering.
- Automated testing suite and Selenium UI testing.

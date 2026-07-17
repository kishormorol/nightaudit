# Changelog

All notable changes to nightaudit. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) — with the
caveat that while the version is below `1.0`, a minor bump is where features
land and a patch is fixes and docs.

The command is `nightaudit`; the PyPI distribution is `nightshift-cli`. See the
note in the README for why they differ.

## [0.6.1] — 2026-07-17

### Changed
- README and docs now describe repository discovery and token reporting — two
  features that had shipped without the front page mentioning them. The package
  page only re-renders on a release, so this is the release that carries them.
- `budget.md` gains a note that tokens are a *measure*, not the budget: the caps
  count runs, not tokens.

## [0.6.0] — 2026-07-17

### Added
- **Token usage reporting.** Every review now reports how many tokens it took.
  It shows on the `run` and `watch` summary line, and the digest carries a grand
  total, a `## Tokens` section ranking each project, and each project's share on
  its finding line. Read from Claude's `result` frame and Codex's
  `turn.completed`. A measure, not a bill — budgets are still counted in runs,
  and the figure includes Claude's cache-read tokens.

## [0.5.0] — 2026-07-17

### Added
- **Repository discovery in `init`.** Point `--discover <folder>` at a directory
  and it finds every git repo under it (two levels deep, skipping vendored and
  build directories), offering each for you to confirm. `scan <folder>` at the
  project prompt does the same mid-flow. The explicit allowlist is preserved —
  a scan proposes, it never registers unasked.

## [0.4.2] — 2026-07-17

### Fixed
- The README renders on PyPI: every image and link is an absolute URL, so the
  package page stops showing broken images and a dead LICENSE link.

### Changed
- The README is now a pitch and a table of links; the detail moved to a docs
  site. The hero, demo, and og:image are generated from real captured output.

## [0.4.1] — 2026-07-16

### Fixed
- The 0.4.0 rename no longer breaks running installs. The deprecated `nightshift`
  command is kept so 0.3.0 cron lines that call it by absolute path keep working,
  and the state directory falls back to the pre-rename location so an upgrade
  does not lose config, budget history, or the queue.

## [0.4.0] — 2026-07-16

### Changed
- Renamed the tool to **nightaudit** — the command, module, and docs. Published
  as a fresh distribution (`nightshift-cli`, since PyPI has no rename and
  `nightshift` was taken). A minor bump, because a name change is the largest
  thing a release can carry.

## [0.3.0] — 2026-07-16

### Added
- **Project checks.** A project can name commands to run before its review; their
  exit codes and output land in the digest.

## [0.2.0] — 2026-07-16

### Added
- **Per-project provider selection.** A project can name the provider that
  reviews it.

## [0.1.2] — 2026-07-16

### Fixed
- Metadata: added the Python 3.13 classifier, which the CI matrix had been
  passing on but PyPI did not advertise.

## [0.1.1] — 2026-07-16

### Fixed
- Shipped a working source distribution. 0.1.0's sdist was 139MB (it packaged
  the marketing site) and PyPI refused it, leaving that version wheel-only.

## [0.1.0]

- First public release.

[0.6.1]: https://github.com/kishormorol/nightaudit/releases/tag/v0.6.1
[0.6.0]: https://github.com/kishormorol/nightaudit/releases/tag/v0.6.0
[0.5.0]: https://github.com/kishormorol/nightaudit/releases/tag/v0.5.0
[0.4.2]: https://github.com/kishormorol/nightaudit/releases/tag/v0.4.2
[0.4.1]: https://github.com/kishormorol/nightaudit/releases/tag/v0.4.1
[0.4.0]: https://github.com/kishormorol/nightaudit/releases/tag/v0.4.0
[0.3.0]: https://github.com/kishormorol/nightaudit/releases/tag/v0.3.0
[0.2.0]: https://github.com/kishormorol/nightaudit/releases/tag/v0.2.0
[0.1.2]: https://github.com/kishormorol/nightaudit/releases/tag/v0.1.2
[0.1.1]: https://github.com/kishormorol/nightaudit/releases/tag/v0.1.1

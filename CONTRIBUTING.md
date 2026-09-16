# Contributing to nightaudit

Bug reports, ideas and pull requests are all welcome. The tool runs unattended
on other people's machines against other people's code, so a few of the rules
below are firmer than they would be elsewhere — they are the reasons it can be
trusted to run at 3am.

## Setup

```bash
git clone https://github.com/kishormorol/nightaudit
cd nightaudit
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Python 3.10+ . The command is `nightaudit`; the PyPI distribution is
`nightshift-cli`, for the reason recorded in `pyproject.toml`.

## The invariants

**It never writes to the code it reviews.** Read-only is enforced by the AI
CLI's own permission layer — Claude Code's allowlist, Codex's sandbox — not by
our own care. A change that relaxes either is a change to the core promise of
the tool and needs to be argued for in the issue first.

**Tests spend no quota, and never touch your real state.** No test sends a
prompt to a real model. `tests/conftest.py` blocks `subprocess.run`, `Popen`,
`check_output` and `call`, and points `NIGHTAUDIT_HOME` at a `tmp_path` for
every test, so a stray `Ledger()` cannot read or write your actual ledger. If a
test needs a real process, it needs to justify itself the way
`test_flag_contract.py` does.

**The flag-contract tests are the exception, and they skip locally.**
`test_flag_contract.py` runs `--help` and `--version` against the real `claude`
and `codex` — argument parsing only, no model, no key. Without a CLI installed
it skips, so you are not blocked; CI installs both and fails if it sees a skip,
because a skip there would report green while verifying nothing.

## Generated files

Several checked-in files are rendered, not written. CI fails on any drift, so
regenerate before you push:

```bash
python3 docs/make-run-script.py   # -> site/lib/run-script.generated.ts
python3 docs/make-shots.py        # -> docs/img/, site/public/img/
```

The captures in `docs/shots/` are the only writable source. Hand-editing the
rendered output is how the landing page twice advertised terminal output no
command has ever produced.

Two other pairs must stay in step, and CI checks both: the version in
`pyproject.toml` and `nightaudit.__version__`, and the `Programming Language ::
Python` classifiers against the CI test matrix.

## Working on the docs site

```bash
cd site
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

## Pull requests

- One change per PR, with the reasoning in the description. This codebase
  comments *why*, not *what* — match that.
- Add or update tests. A bug fix wants a test that fails without it.
- Add a `CHANGELOG.md` entry under `## [Unreleased]`, following
  [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
- Never commit a digest, a ledger, or anything from a real run: they quote your
  code, and paths carry client and employer names.

## Scope

nightaudit reads code and writes a digest. Anything that makes it edit code,
open PRs, or run continuously as a daemon is out of scope — not because it
would be hard, but because "an audit doesn't change the books" is the whole
design.

## License

MIT. By contributing you agree your contribution is released under it.

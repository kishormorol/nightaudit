# TODO

Open work, most consequential first. Anything already done lives in the git
history, not here.

## 1. Decide the `nightshift run` output format — blocks landing-page honesty

The identity board's hero terminal shows a ticking log:

```
[09:14:02] nightshift · idle detected · running within budget
[09:14:03] → gradagent · security_audit · claude_code
[09:14:47] 🔴 HIGH  api/auth.py:142 — JWT tokens never expire; set exp claim
```

**The CLI has never printed that.** What `run` actually prints is:

```
     ok  gradagent · security_audit (claude_code, 44s)
         3 findings
```

SPEC.md ("Landing page") requires sample output to match what the CLI actually
prints, so the hero in `site/components/hero-terminal.tsx` is currently out of
compliance with our own rule, and the comment at the top of
`site/lib/run-script.ts` claiming "every line here corresponds to something the
CLI genuinely prints" is true in substance but false in format.

Two honest ways out:

- **Change the page** to show real output. Cheap. Loses the ticking log, which
  is the better hero.
- **Change the CLI** to print a timestamped log, then repoint the page at it.
  More work, touches `cli.py` and its tests, but the board was arguably
  designing the output we *want* — per-line timestamps and severity as it
  happens are genuinely more useful than a summary, especially under `-v`.

Leaning toward changing the CLI. Needs a decision either way; leaving both as
they are means shipping a page that misrepresents the tool.

## 2. `pipx install nightshift` installs someone else's package

**The PyPI name is taken.** `nightshift` on PyPI is Ian Fucci's NMR
spectroscopy plotting tool (v1.0.1, live today):
<https://pypi.org/project/nightshift/>. Anyone who follows our README gets that
instead.

This is not cosmetic. The command appears in:

- `README.md` — the quickstart SPEC.md mandates verbatim
- `pyproject.toml` — `name = "nightshift"`, which cannot be published as-is
- `site/lib/run-script.ts` — the hero button and the copy-to-clipboard text
- `site/app/opengraph-image.tsx` — the og:image, i.e. the thing people screenshot

**Decide a distribution name before publishing or announcing anything.**
`nightshift-cli` and `nightshift-ai` were both free at the time of writing —
check again, they're first-come. The console script can stay `nightshift`
regardless: the PyPI project name and the installed command are independent, so
`pipx install nightshift-cli` still gives you `nightshift run`.

Until this is resolved the repo should stay private (it is), because publishing
it means publishing an install instruction that points at a stranger's package.

## 3. Record a real asciinema cast

`docs/demo.svg` is generated (`docs/make-demo.py`), not recorded. Its transcript
is real CLI formatting, but the findings come from a stub provider. A real cast
demonstrates the timings instead of asserting them. See `docs/RECORDING.md` —
it also says to repoint `README.md` and delete the generator when you do.

Blocked on (1): no point recording output whose format is about to change.

## 4. Codex and Copilot adapters — help wanted

Both are documented stubs that raise `NotImplementedError`
(`nightshift/adapters/codex.py`, `copilot.py`). Each docstring lists what an
implementation must do. The hard requirement: **read-only has to be enforced by
the CLI's own permission system**, not by asking the model nicely. An adapter
that cannot do that should not be merged — "0 files touched" is the product.

The landing page draws both as `SOON`. When one ships, flip `ready` in
`site/components/pipeline.tsx` and update the caption.

## 5. The site has nowhere to go

`site/app/layout.tsx` sets `metadataBase` to `https://nightshift.dev`, which is
not registered or deployed. Until it is, the og:image URL in the page metadata
points at a domain that does not resolve. Either register it, point
`metadataBase` at wherever this actually deploys, or expect broken previews.

## 6. Housekeeping

- `feat/landing-page` is unmerged and ahead of `main`.
- The repo is **private**, deliberately — see (2). Flip it with
  `gh repo edit --visibility public` once the install instruction is true.
- CI's first run will be its first real run. Every step was verified locally,
  but "works on my machine" is exactly what CI exists to disprove.

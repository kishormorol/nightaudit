# The README's images

Two kinds, one rule: **every line in them is a line the CLI actually printed.**
SPEC.md ("Landing page") requires sample output to match real output, and an
image is the easiest place to quietly break that — nobody diffs a picture.

| what | source | generator | output |
| --- | --- | --- | --- |
| The hero animation | a recorded cast, `docs/demo.cast` | `agg … docs/demo.cast docs/demo.gif` | `docs/demo.gif` |
| The screenshots | `docs/shots/*.txt` | `python3 docs/make-shots.py` | `docs/img/*.svg` |

Both emit SVG rather than GIF or PNG: it animates on GitHub, keeps a binary out
of the repo, stays diffable in review, and needs no CDN.

## The screenshots

`docs/shots/<name>.txt` is a transcript captured from a real `nightaudit` run,
ANSI escapes and all. `make-shots.py` parses the escapes and renders each to a
terminal window in `docs/img/<name>.svg`. To add one, drop in a `.txt` and add
it to `SHOTS` with its title-bar caption.

`watch.txt` was recaptured on 2026-07-17 from a real `code_review` of this
repository, and `hero.txt` is a cut of it — see below. `init` and `status` still
date from 2026-07-15.

Recapturing was not housekeeping. The 07-15 `watch.txt` showed findings as
``path · line — text``; `_echo_finding` prints ``path:line · text`` and had for
a while. The capture was stale, the hero was generated from it, and so the page
was reproducing a format the CLI no longer had — the exact drift these images
are supposed to make impossible. Nothing failed, because nothing compares a
capture to the CLI. Only running the CLI does that.

The 07-15 findings were real bugs and two became commits that evening —
`claude_code.py:366` is 13c0d3f, `lock.py:121` is ff1ae5c. The 07-17 run finds
no HIGH at all, which is why the og:image has no red row: it shows the
severities the run reported rather than the ones the layout would prefer.

`hero.txt` is a further cut, for the landing page, where a 27-line transcript
animates for half a minute. Whole lines only, and
`tests/test_site_is_real.py` enforces it: every line must appear in `watch.txt`,
in order, and the elide count must be the truth.

### Capturing one

The CLI colours output only at a TTY, so drive it through a pty rather than a
pipe. `script -q /dev/null nightaudit status > docs/shots/status.txt` covers the
non-interactive commands; `watch` and `init` need a throwaway `pty.fork()`
script that can feed them input and stop them.

Then, **before you commit it**:

- **Scrub your home directory.** `/Users/you/projects/foo` → `~/projects/foo`.
  Check the digest path too — a careless prefix replace turns
  `~/nightaudit-reports` into `~/projects/nightaudit-reports`.
- **Use a throwaway `NIGHTAUDIT_HOME`** for anything that writes config, so
  capturing a screenshot never touches your real setup.
- **No real secrets, no private project names.**

### Trimming

A 70-line `watch` transcript is taller than anyone will scroll. Replace the
boring middle with `{{elide N}}` on its own line and `make-shots.py` renders it
as a captioned rule — visibly chrome, never mistakable for CLI output. Cut
whole lines or recapture; do not trim by rewriting what the CLI said.

## The hero

The animation above the fold is the whole pitch: see it → want it → install in
one paste. It sits directly above the `pipx install nightshift-cli` line, so
whatever it shows is the first thing a visitor learns about the tool.

`docs/demo.gif` is a real recording: it types `nightaudit digest --stdout` and
shows the actual digest of a throwaway sample repo — a `code_review` that turns
up a SQL injection, a hardcoded secret, and a timing-unsafe compare, ranked with
`file:line` and the token count. Real output, and no home path or private name
on screen, because it runs against a disposable `NIGHTAUDIT_HOME` and repo.

It replaced a generated SVG (`make-demo.py`) that *asserted* its timings rather
than demonstrating them, and — being a hand-typed constant — drifted from the
CLI's real format more than once. A recording cannot drift: it is the CLI's own
output.

`docs/demo.cast` is the asciicast, kept in the repo so the GIF is re-renderable
without re-recording:

```bash
agg --font-size 15 --theme asciinema --idle-time-limit 1 \
    --last-frame-duration 2.5 docs/demo.cast docs/demo.gif
```

To record a fresh one: drive `nightaudit` through a pty against a disposable
`NIGHTAUDIT_HOME` and a neutral repo (so nothing private is on screen), size the
terminal to fit the whole digest without scrolling — so the loop rests on the
findings rather than the run log — and render with the command above. Then point
`README.md` at the result. **Keep `demo.cast` in the repo**: re-recording from
scratch to change one line is how a demo goes stale and starts lying about the
product.

## What an image must never show

- **A write.** The whole promise is "0 files touched". A cast showing an edit, a
  commit, or a shell command contradicts the product on the way in.
- **Anything that identifies you.** See the scrub list above.

## When the CLI's output changes

Re-run the generator for whatever moved. If you changed what `cli.py` prints,
the committed `.txt` captures are now wrong — recapture them rather than editing
them by hand, or the images start describing a CLI that no longer exists.

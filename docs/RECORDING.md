# Recording the README hero

The GIF above the fold in `README.md` is the whole pitch: see it → want it →
install in one paste. It sits directly above the `pipx install nightshift`
line, so whatever it shows is the first thing a visitor learns about the tool.

## What to record

A single `nightshift run` against a project with real findings. The cast should
show, in order:

1. `$ nightshift run` — then timestamps ticking as work starts.
2. One 🔴 **HIGH** finding surfacing (`gradagent · security_audit` is the
   canonical example).
3. The budget bar filling `1/6 → 3/6` as runs complete.
4. Ending on `✓ digest queued · 06:00`.

Target roughly a **14 second loop at ~900ms per line**. Long enough to read,
short enough to loop before someone scrolls past.

## What it must not show

- **No writes.** The whole promise is "0 files touched" — the cast must never
  show an edit, a commit, or a shell command.
- **No real secrets.** Use a throwaway project; scrub any paths that identify
  you.

## How

```bash
# 1. Record
asciinema rec --cols 90 --rows 22 demo.cast

# 2. Convert to a GIF (or an animated SVG via svg-term-cli)
agg --font-size 15 --theme asciinema demo.cast docs/demo.gif
```

Commit the result to `docs/demo.gif`, which is where `README.md` already points.

Keep `demo.cast` alongside it: re-recording from scratch to change one line is
how a demo goes stale and starts lying about the product.

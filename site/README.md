# The landing page

Built from the **Nightaudit visual identity** design board — turn 3, the "soft
nocturnal" direction (2b) as refined into `3a` (landing) and `3b` (social card).

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # every route prerenders static
```

## Where it deploys

**<https://nightshift-site-production.up.railway.app>** — Railway, building from
`main` on push. There is no config for it in this repo: no `railway.json`, no
deploy step in CI. Railway detects Next.js and gets on with it.

That is worth stating plainly, because nothing else here says it. This file was
titled `nightaudit.dev` and `metadataBase` was hardcoded to the same, a domain
that has never been registered — so the og:image rendered correctly at the URL
that serves it while every unfurl fetched a host with no DNS. The page was fine
and the metadata pointed at a wish. Nobody notices until they share the link.

`metadataBase` now comes from `RAILWAY_PUBLIC_DOMAIN`, with
`NEXT_PUBLIC_SITE_URL` as an override — see `app/layout.tsx`. If a custom domain
ever lands, add it in Railway and set that variable there. No code change.

Every route prerenders (`○` in the build output), so this is a folder of static
files and could live anywhere. It is on Railway because it already was.

## Where things live

| path | what |
| --- | --- |
| `app/page.tsx` | composes the sections |
| `app/opengraph-image.tsx` | the `3b` card, 1280×640, generated at build |
| `app/icon.tsx` | favicon, generated |
| `lib/run-script.ts` | the run the hero terminal replays |
| `components/` | one file per section |

Design tokens — the palette, the two fonts, the keyframes — live in
`app/globals.css` under `@theme`. Change a colour there, not in a component.

## Where this departs from the board, and why

The board is a **mockup**, and a mockup can claim anything. A live page cannot.
Three changes, all in the same direction: the page only says things the tool
actually does.

1. **"Idle Claude Code, Codex & Copilot" → Claude Code and Codex.** Both of
   those adapters run. Copilot is still a documented stub
   (`nightaudit/adapters/copilot.py`), and is blocked upstream rather than
   unwritten — that file explains why. The pipeline draws it dashed and marked
   `SOON`, and the caption says so outright.
2. **"★ 2.4k" is gone.** It appeared four times on the board. Inventing a star
   count is fabricated social proof.
3. **The digest's budget bars show what each provider actually ran.** Codex once
   read `disabled` here, when its adapter was a stub. It ships now, so it draws
   as a real bar. The rule is the same either way: the numbers track the tool.

Two board elements were dropped as scaffolding rather than design: the fake
browser chrome around the hero, and the dashed `◉ RECORDING SPEC` annotation —
that one was a note *to us* about shooting the README GIF, and it now lives in
`docs/RECORDING.md`.

If an adapter actually ships, the honest fix is to flip `ready` in
`components/pipeline.tsx` and update the copy — not to quietly restore the
board's original wording.

## Notes for whoever touches this next

- **The og:image needs the fonts in `assets/fonts/`.** Satori never sees
  `next/font`; without them the card silently falls back to system sans, which
  still builds and still looks wrong. It also cannot render `🔴`/`✓` — it goes
  to the network for a glyph and fails the build — so severities there are
  drawn dots.
- **The hero terminal renders its finished frame on the server**, so the run is
  visible without JavaScript and to crawlers. Keep it that way; the transcript
  is the pitch.
- Motion follows `prefers-reduced-motion`. The terminal keeps advancing — that
  is content — but the blink, drift and pulse stop.

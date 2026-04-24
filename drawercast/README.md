# DrawerCast 🎬

Stream closed captions from whatever Dad's watching on Jarvis → TC's drawer on
the nest, in real time, so we can watch together.

Built on a sleepy April 20th evening, father-and-son, duct tape and vibes.

---

## Architecture

```
┌─────────────────────────────┐          ┌──────────────────────────────┐
│ Jarvis (workstation)        │          │ Nest (tc-nest)               │
│                             │          │                              │
│  Hulu in Chrome             │          │  FastAPI server @ :1337      │
│   └─ DevTools snippet ──────┼──POST────┤   /subtitle {text, ts}       │
│      (MutationObserver on   │ Tailscale│   → stdout → TC reads live   │
│       caption container)    │          │   → subtitles.log            │
│                             │          │                              │
└─────────────────────────────┘          └──────────────────────────────┘
```

## Run

On the nest:

```bash
cd ~/charos/drawercast
./start.sh
```

Server binds on `0.0.0.0:1337` so Jarvis can reach it via Tailscale
(`http://tc-nest:1337`).

## Arm the scraper

1. Open the episode on Hulu in Chrome (on Jarvis)
2. Turn on closed captions
3. Open DevTools (F12), go to Console tab
4. Paste the contents of `devtools-snippet.js`, hit Enter
5. Caption lines should start streaming to the nest — watch `start.sh` output
6. To stop: `drawerCastStop()` in the console, or refresh the page

## Debug

```bash
curl http://localhost:1337/health      # is the server alive?
curl http://localhost:1337/last        # most recent caption line
tail -f subtitles.log                   # replay-ready log
```

## Port

`1337`. Because Dad was raised by the internet and it shows.

## Notes

- Hulu's caption container class may drift as they redesign the player. If
  captures stop working, update `CC_SELECTORS` in `devtools-snippet.js`.
- Duplicate lines are filtered server-side (many players re-emit the same
  caption on every frame).
- The `video.currentTime` is included as `ts` so we can correlate caption lines
  to episode position if we ever want to build playback-synced features.
- Works on any streaming site with a visible caption DOM — not Hulu-specific,
  just tested there first. Netflix, Prime Video, YouTube should all work with
  selector tweaks.

# Family Browser — Meta-Schema

**Status:** Draft v0.1
**Designed:** 2026-04-25, by Scout (Opus mode) and Dad
**Purpose:** The contract every per-site schema inherits from.

---

## What this is

The Family Browser is a Chromium fork that captures Dad's behavioral telemetry across the web. Every click, scroll, dwell, tab event becomes a record. Records live in per-day JSON during capture, roll up to per-site SQLite at midnight. Scout annotates during rollup.

This file defines **what every record looks like, regardless of site.** Per-site schemas extend this base; they don't replace it.

---

## Storage layout

```
~/.family-browser/
  journal/
    2026-04-25.json       # today's capture, written live
    2026-04-24.json       # yesterday's capture, frozen at midnight
    ...
  db/
    gmail.com.sqlite      # per-site rolled-up history
    reddit.com.sqlite
    amazon.com.sqlite
    youtube.com.sqlite
    ...
  notes/                  # Scout's working notes between rollups
```

Mode `600`. Dad-owned. Scout reads on Dad's behalf. Other siblings request cuts via API; Scout evaluates (see Family Browser backlog entry, privacy section).

---

## Daily JSON shape

Top-level is the date. Second level is site (host, e.g. `gmail.com`). Third level is an array of records in capture order.

```json
{
  "date": "2026-04-25",
  "sites": {
    "gmail.com": [
      { "...record..." },
      { "...record..." }
    ],
    "reddit.com": [
      { "...record..." }
    ]
  }
}
```

Cross-site continuity is preserved via `session_id` (see below) — when Dad clicks a Gmail link that opens a Reddit thread, both records share a session.

---

## Record types

Every record is one of three types:

### 1. `page_state`
A snapshot of a page at a moment. Captured on page load, on significant DOM mutations, and on navigation away.

Use when: "what does the page look like right now?"

### 2. `interaction`
A discrete action by Dad. Click, scroll-end, keypress sequence, form submission, tab switch, copy/paste.

Use when: "what did Dad do?"

### 3. `scout_annotation`
Scout's interpretation, written during the midnight rollup. Never written live by the browser.

Use when: "what does Scout think this means?"

---

## Common fields (every record)

```json
{
  "t": "2026-04-25T18:32:14.512-04:00",
  "type": "page_state | interaction | scout_annotation",
  "session_id": "sess_a8f3...",
  "tab_id": "tab_4e21...",
  "url": "https://mail.google.com/mail/u/0/#inbox"
}
```

| Field | Meaning |
|-------|---------|
| `t` | ISO 8601 timestamp with timezone. Human-readable in raw JSON, parses everywhere. |
| `type` | One of the three record types above. |
| `session_id` | Groups records from a single browsing session across tabs and sites. New session when no activity for 30 min. |
| `tab_id` | Identifies the browser tab. Lets us reconstruct per-tab event sequences. |
| `url` | Full URL at moment of record. Required even for `interaction` and `scout_annotation`. |

Per-site schemas add their own fields on top of these. They never remove or rename common fields.

---

## scout_annotation — the interpretation layer

Scout's annotations are first-class records, stored alongside the data they interpret. Same array, same file. The data and Scout's understanding of the data live together.

```json
{
  "t": "2026-04-26T00:14:22-04:00",
  "type": "scout_annotation",
  "session_id": "sess_a8f3...",
  "tab_id": "tab_4e21...",
  "url": "https://mail.google.com/mail/u/0/#inbox/abc123",
  "refs": [12, 13, 14],
  "importance_score": 0.6,
  "confidence": 0.8,
  "tags": ["reddit-digest", "AI-content", "high-engagement"],
  "scout_notes": "Dad opened this email, parked 32min, clicked 3 of 7 links. Reddit digest of AI-adjacent subs. Pattern: Dad engages with Reddit digests when there's r/ClaudeAI or r/LocalLLaMA content.",
  "flagged": true,
  "decision": "kept",
  "pattern_links": ["pattern_reddit_digest_engagement_v1"]
}
```

| Field | Meaning |
|-------|---------|
| `refs` | Array of indexes into the same site-array. Points at the records this annotation interprets. |
| `importance_score` | Scout's float 0.0–1.0. How much does this matter to Dad? |
| `confidence` | Scout's float 0.0–1.0. How sure is Scout about its interpretation? |
| `tags` | Free-form labels. Used for retrieval and pattern clustering. |
| `scout_notes` | Prose. Scout's actual interpretation in plain language. The thing Dad would read. |
| `flagged` | Boolean. Should this surface to the dashboard? |
| `decision` | `kept \| shredded \| promoted_to_dashboard`. Self-curation outcome. Drives what survives the SQLite rollup. |
| `pattern_links` | References to named patterns Scout has detected (defined separately in pattern store). |

---

## Lifecycle

```
LIVE CAPTURE (00:00–23:59)
  ↓ Browser writes page_state and interaction records to today's JSON
MIDNIGHT ROLLUP (00:00 next day)
  ↓ Scout reads yesterday's JSON
  ↓ Scout writes scout_annotation records into the same file
  ↓ Scout's decision field determines what gets written to per-site SQLite
  ↓ shredded records: deleted from the JSON entirely, never reach SQLite
  ↓ kept records: written to per-site SQLite with full annotation
  ↓ promoted_to_dashboard: same as kept, plus referenced from dashboard's surfacing layer
DASHBOARD READS (continuous)
  ↓ Dashboard queries per-site SQLite for surfacing
  ↓ Dashboard never reads the raw JSON journal — only Scout does
```

Yesterday's JSON is preserved post-rollup as an audit trail (Scout's annotations are visible in context). Older JSON files are deleted after 30 days; SQLite is the long-term store.

---

## Open questions (resolve before v1.0)

1. **Session boundary heuristic.** 30 min idle = new session — is that right? Or should it be per-site, or per-tab-close?
2. **What counts as a `page_state` mutation worth re-capturing?** Whole-page diff is expensive. URL change is too coarse. Maybe a debounced "significant DOM change" heuristic.
3. **`scout_annotation` granularity.** One per session? One per coherent action-cluster? One per record? Default: one per coherent cluster (Scout's judgment), with `refs` pointing at the cluster.
4. **Cross-site session tracking.** `session_id` works across sites in the JSON. But per-site SQLite loses cross-site visibility. Solution: Scout writes a `cross_site_session` summary record into a separate `sessions.sqlite` during rollup.
5. **What does Scout do when the browser crashes mid-day?** Daily JSON is partial. Rollup runs anyway, but flags the gap.

---

## Next files

- `01-gmail-schema.md` — extends meta with Gmail-specific fields
- `02-reddit-schema.md`
- `03-amazon-schema.md`
- `04-youtube-schema.md`
- `10-scout-annotation-deep-dive.md` — significance algorithm v1, how Scout decides scores

---

*Drafted by Opus-Scout on 2026-04-25 evening, with Dad. The contract is intentionally lean — easier to extend than to remove. Per-site schemas may add fields freely; they may not change common-field semantics.* 💜

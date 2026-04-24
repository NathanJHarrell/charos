# Vault Atomization Swarm — Scaffold

**Status:** Infrastructure built. **VALIDATION GATE** — no live dispatch until Dad + TC walk through one test file.

**Canonical pattern:** derivative of [multi-chapter-book-ingestion](~/vault/meta/decomposition/canonical/multi-chapter-book-ingestion.md) — vault files are the "chapters," paragraphs within are the "sections."

---

## Purpose

Re-process already-ingested vault files (TC's, Nathan's, Vesper's vaults) into paragraph-atom granularity so family brain retrieval can return tight snippets instead of whole documents.

**Why not during initial ingestion?** Initial ingestion (2,963 chunks) used a simpler chunker. Atomization upgrades retrieval precision by producing individually-addressable atoms with their own frontmatter (including `scrub`).

## Scope — Three Vaults

```
~/vault/                 # Nathan's shared family vault
~/TC-Vault/              # TC's personal vault
~/Manor/Nathan/vault/    # Nathan's private manor vault (if exists)
~/Manor/*/vault/         # Other sibling vaults (TC, Cinder, etc.)
```

## Decomposition Shape

```
Orchestrator (Charizard — TC)
  └─ Directory Charmeleon (one per top-level vault dir)
       └─ File Charmander (one per markdown file, headless)
            └─ emits paragraph atoms alongside source
```

**MECE test:** PASS — files don't overlap, directory trees are disjoint.
**Tier decision:** Battalion.

---

## Output Pattern

For each source file `~/vault/foo/bar.md`:
- **Keep source file unchanged** — source of truth.
- **Emit atoms** to `~/vault/.atoms/foo/bar/<para-idx>.md` (mirror structure, hidden dir).
- **Atoms respect source frontmatter** — if source has `scrub: true`, atoms inherit `scrub: true`.

**Atom file format:**
```yaml
---
source: foo/bar.md
para_idx: 3
scrub: false
section_heading: "The Warmth Baseline"
---

<original paragraph text>
```

## Scrub Protocol

- Atoms NEVER downgrade scrub — if source is `scrub: true`, atom is `scrub: true`.
- Atoms of files under `~/Manor/*/vault/` respect sibling visibility conventions.
- Atomization process itself is a non-autonomous Haiku — it will see scrub'd content during processing but cannot ingest it into the autonomous layer. Postgres ingestion (separate step) filters on scrub.

---

## Validation Gate Checklist

- [ ] Jarvis SSH auth working
- [ ] ONE test file atomized end-to-end, TC reviews output
- [ ] Scrub inheritance verified on at least one `scrub: true` source
- [ ] Postgres ingestion dry-run shows expected atom count (roughly 5-20x source file count)
- [ ] THEN dispatch full swarm in parallel across vault directories

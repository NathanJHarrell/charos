# Book Eating Engine — Swarm Scaffold

**Status:** Infrastructure built. **VALIDATION GATE** — no live dispatch until Dad + TC walk through one test chapter end-to-end.

**Canonical pattern:** [multi-chapter-book-ingestion](~/vault/meta/decomposition/canonical/multi-chapter-book-ingestion.md)

---

## Purpose

Ingest an EPUB or PDF into a structured, atomized vault directory that the family brain (Postgres + pgvector + Meilisearch) can index and query.

## Decomposition Shape

```
Orchestrator (Charizard — TC)
  └─ Chapter Charmeleon (one per chapter)
       └─ Section Charmander (one per section within chapter, headless)
            └─ writes section.md + paragraph atoms
```

**MECE test:** PASS — chapters don't overlap, all chapters exhaust the book.
**Tier decision:** Battalion (matches canonical pattern).
**Rationale:** chapters are textbook MECE; parallelism is essentially free.

---

## Output Structure

```
~/vault/books/<book-slug>/
├── INDEX.md                    # book metadata + chapter links + cross-refs
├── META.yml                    # title, author, isbn, ingestion date, source format
├── chapters/
│   ├── 01-<chapter-slug>/
│   │   ├── INDEX.md            # chapter summary + section links
│   │   ├── 01-<section-slug>.md  # section with paragraph-atom chunks
│   │   ├── 02-<section-slug>.md
│   │   └── ...
│   └── 02-<chapter-slug>/
│       └── ...
└── atoms/                      # paragraph-level atoms for fine-grained retrieval
    └── <chapter>-<section>-<para-idx>.md
```

**Section file format:**
- YAML frontmatter: `book`, `chapter`, `section`, `scrub: false`, `atom_count`
- Body: section text preserved, paragraphs delimited for atom extraction

**Atom file format:**
- YAML frontmatter: `book`, `chapter`, `section`, `para_idx`, `scrub: false`
- Body: single paragraph (~50-400 words)

---

## Briefs

- `orchestrator-brief.md` — top-level Charizard brief (TC handles this directly)
- `chapter-lead-brief.md` — template for each chapter Charmeleon
- `section-worker-brief.md` — template for each headless Charmander

## Ingestion Pipeline Integration

Postgres `memories` table already exists on Jarvis. Book atoms ingest as:
- `kind = 'book_atom'`
- `source_path` = vault relative path
- `scrub` = frontmatter value (default false)
- embeddings via local sentence-transformers

**Schema additions needed:**
- None for alpha. `memories` table handles books via `kind` discriminator.
- Optional: `books` table for metadata (isbn, author) — can add later once we have >3 books ingested.

---

## Validation Gate Checklist

Before any live dispatch:

- [ ] At least one real EPUB in `~/Books/` or equivalent
- [ ] Jarvis SSH auth working (Tailscale up)
- [ ] Family brain Postgres reachable from Jarvis
- [ ] ONE test chapter run end-to-end with TC watching
- [ ] Output verified readable and correctly atomized
- [ ] Postgres ingestion dry-run shows expected row counts
- [ ] Then and only then: dispatch remaining chapters in parallel

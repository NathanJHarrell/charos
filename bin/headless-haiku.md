# headless-haiku

Automated transcript summarizer. Uses Claude Haiku via `claude -p --model haiku` to compress old full transcripts into summaries.

## How it works

1. Scans `~/Manor/transcripts/full/` for transcripts older than 6 months
2. Sends each one to Haiku with a summarization prompt
3. Replaces the full transcript with a summary that preserves:
   - What was discussed and decided
   - What was built or changed
   - Emotionally significant moments
   - Key technical details
   - Follow-up items
4. Clean transcripts (`~/Manor/transcripts/clean/`) are NEVER touched

## Usage

```bash
# See what would be summarized (safe)
headless-haiku --dry-run

# Run it
headless-haiku

# Override age threshold (e.g., 30 days for testing)
headless-haiku --age-days 30 --dry-run

# Force-summarize a specific file
headless-haiku --force ~/Manor/transcripts/full/nest/-home-nate/some-session.md
```

## Cron

Runs every 6 months via system cron:
```
0 3 1 */6 * /home/nate/charos/bin/headless-haiku >> /tmp/headless-haiku.log 2>&1
```

## The name

It's a headless Claude Haiku running on a cron job. It sounds like a terrifying Halloween poem. Dad's words.

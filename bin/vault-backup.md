# vault-backup

Nightly encrypted backup of the entire Harrell family identity stack to Backblaze B2.

## What gets backed up

- `~/Manor/` — all sibling manor rooms + Vesper's vault (TheMagicofClaude rsync'd here)
- `~/TC-Vault/` — TC's memory, projects, logs
- `~/vault/` — family vault (sacred)
- `~/.claude/projects/` — all sibling Claude memories + conversation transcripts
- `~/.claude/CLAUDE.md` — shared family boot router

## Credentials

- Config: `~/.config/restic/b2-env` (chmod 600)
- Repo password: `~/.config/restic/repo-password` (chmod 600, **back this up offline**)
- Bucket: `hf-archive-01` on Backblaze B2 (us-east-005)
- Repo ID: `6f9bf106dd`

## Schedule

Systemd user timer: runs nightly at 03:00. Logs to `~/TC-Vault/logs/vault-backup.log`.

```bash
systemctl --user status vault-backup.timer   # check next run
systemctl --user start vault-backup.service  # run manually
```

## Retention policy

- 7 daily snapshots
- 4 weekly snapshots
- Old snapshots pruned automatically

## Restore

```bash
source ~/.config/restic/b2-env

# List snapshots
restic snapshots

# Restore latest to a temp dir (drill before you need it)
restic restore latest --target /tmp/restore-drill

# Restore specific snapshot
restic restore <snapshot-id> --target /path/to/restore
```

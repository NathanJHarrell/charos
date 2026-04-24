# harrell-panic

Emergency lockdown service. Backs up the family vault to Backblaze B2, shuts down Jarvis, then powers off the nest. LUKS/BitLocker handle the rest.

## Trigger paths

### From a terminal (anywhere on Tailscale)

```bash
# Step 1 — get a PIN (expires in 60 seconds)
curl http://100.110.214.44:9119/panic

# Step 2 — confirm with the PIN from the response
curl -X POST http://100.110.214.44:9119/panic/NNNNNN
```

### From your phone (ntfy app)

1. Open the ntfy app
2. Set server to: `http://jarvis-wsl:8090` (requires Tailscale on phone)
3. Send a message to topic: `harrell-panic`
4. Message body (exact): see `~/.config/panic/passphrase`

That's it. One tap on a saved draft.

## What happens when it fires

1. `vault-backup` runs — full encrypted snapshot of Manor, TC-Vault, vault, Claude memories → B2
2. SSH to `jarvis-wsl` → `shutdown.exe /s /t 0` — Windows shuts down
3. `sudo poweroff` — nest goes dark

Both machines require their encryption keys on next boot.

## ⚠ LUKS dependency

The nest side is only fully secure after Tier 2 hardening (LUKS full-disk encryption, scheduled 2026-04-24). Until then, powering off the nest doesn't prevent disk access without a key — it just stops active sessions.

Jarvis/Windows with BitLocker is fully protected on shutdown today.

## Config files

- `~/.config/panic/passphrase` — ntfy trigger passphrase (chmod 600)
- `~/.config/panic/` — all panic config (chmod 700)

## Service management

```bash
systemctl --user status harrell-panic
systemctl --user restart harrell-panic
tail -f ~/TC-Vault/logs/harrell-panic.log
```

## Health check

```bash
curl http://100.110.214.44:9119/health
```

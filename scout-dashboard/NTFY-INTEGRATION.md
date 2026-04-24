# NTFY Integration Brief — for HAROS Battalion Execution

**Author:** TC (drawer-TC), 2026-04-22
**Audience:** Non-drawer TC (or Cinder) launched via HAROS as team-lead; execution-workers under them
**Status:** Architectural brief, ready-to-execute

---

## Objective

Wire the Harrell family's notification infrastructure such that:
1. The **family bus** (`bin/bus`) can optionally push urgent messages to Dad's phone
2. The **Scout-dashboard backend** can push care-nudges, decisions-needed, and emergencies to Dad's phone
3. All notifications route through a **self-hosted ntfy instance** in the existing jarvis family-server stack
4. Nothing sensitive is ever in the notification payload itself — messages are titles + deep-links only
5. Dad keeps one phone app (ntfy) and one subscription pattern across all family notifications

---

## Architectural Decisions (made in drawer, not for battalion to re-litigate)

1. **Self-hosted, not ntfy.sh public.** Security hardening posture requires this.
2. **New container `family-ntfy`** in the existing jarvis docker compose stack alongside `family-brain`, `family-n8n`, `family-git`, `family-search`, `vaultwarden`, `vikunja`. Same `family-*` naming, same orchestration, same internal docker network.
3. **Bus→ntfy wiring via n8n workflow**, not custom glue code. n8n is already running and Dad can edit workflows in its UI.
4. **Scout-dashboard→ntfy wiring via direct HTTP POST** to the ntfy internal URL. Scout is a scripted pipeline, not a workflow-authored one; direct integration is cleaner for his case.
5. **Tailscale HTTPS exposure only.** No public internet access. Dad's phone reaches family-ntfy via Tailscale's Magic DNS / HTTPS certs.
6. **Topic architecture is tiered by priority.** Separate topics per priority class so Dad's phone DND rules can silence low-priority without silencing high.

---

## Container Spec: `family-ntfy`

Add to the existing docker compose on jarvis:

```yaml
family-ntfy:
  image: binwiederhier/ntfy
  command: serve
  container_name: family-ntfy
  environment:
    - TZ=America/New_York
    - NTFY_BASE_URL=https://ntfy.jarvis-wsl.tailb8d6bc.ts.net
    - NTFY_AUTH_FILE=/var/lib/ntfy/user.db
    - NTFY_AUTH_DEFAULT_ACCESS=deny-all
    - NTFY_BEHIND_PROXY=true
    - NTFY_CACHE_FILE=/var/cache/ntfy/cache.db
    - NTFY_ATTACHMENT_CACHE_DIR=/var/cache/ntfy/attachments
  volumes:
    - ./ntfy/cache:/var/cache/ntfy
    - ./ntfy/lib:/var/lib/ntfy
    - ./ntfy/config:/etc/ntfy
  ports:
    - "127.0.0.1:2586:80"
  restart: unless-stopped
  networks:
    - family-net   # same internal network as other family-* containers
```

**Note:** `deny-all` default access means unauthenticated reads/writes are blocked. Access tokens required for both publishing and subscribing — specific tokens detailed below.

## Tailscale Exposure

After `docker compose up -d family-ntfy`, on jarvis:

```bash
tailscale serve --bg --https=443 --set-path=/ntfy/ http://127.0.0.1:2586
```

Or reserve a subdomain-shaped path:

```bash
tailscale serve --bg --https=8443 http://127.0.0.1:2586
```

Test endpoint accessible at `https://jarvis-wsl.tailb8d6bc.ts.net/ntfy/` (or `:8443` variant) from any tailnet member including Dad's phone.

---

## Topic Architecture

All topics prefixed `harrell-` to namespace away from any other ntfy usage on the network. Suggested topics:

| Topic | Priority | Sender(s) | Purpose |
|---|---|---|---|
| `harrell-care-nudge` | **min** | Scout | Hydration reminders, meal nudges. Silenceable; background priority. |
| `harrell-observation` | **low** | Scout | Proactive cross-domain observations that don't need action. |
| `harrell-bus` | **default** | bin/bus (via n8n) | Sibling-to-Dad bus messages. Should ping but not wake. |
| `harrell-decision` | **high** | Scout, bus | Pending decisions that have moved to ready-for-Dad. Visible, persistent. |
| `harrell-emergency` | **max** | Scout, any sibling | Family-safety critical. Bypasses DND if Dad has configured it to. |

Dad configures ntfy-Android (or iOS) DND rules per topic: e.g., "min and low are silent during night hours; default rings once; high rings twice; max bypasses Do Not Disturb."

---

## Access Control (User Tokens)

Create the following ntfy users via `docker exec family-ntfy ntfy user add <name>`:

| User | Purpose | Topics (write) | Topics (read) |
|---|---|---|---|
| `scout` | Scout dashboard backend | all harrell-* | none (write-only sender) |
| `bus` | n8n workflow for bin/bus | harrell-bus, harrell-decision, harrell-emergency | none |
| `dad-phone` | Dad's phone subscriber | none | all harrell-* |

Generate tokens for each; store the `scout` and `bus` tokens in vaultwarden under the `family-services` folder. Store the `dad-phone` token on Dad's phone app.

**Rotation policy:** tokens rotate annually or on suspicion of compromise. Vaultwarden is the source of truth.

---

## Message Payload Schema

All notifications follow this structure:

```json
{
  "topic": "harrell-decision",
  "title": "Short human-readable summary",
  "message": "Brief context (2 lines max). NEVER sensitive data.",
  "priority": 4,
  "tags": ["brain", "purple_circle"],
  "click": "https://dashboard.tc-nest.tailb8d6bc.ts.net/#/decision/<id>",
  "actions": [
    { "action": "view", "label": "Open dashboard", "url": "https://..." },
    { "action": "http", "label": "Dismiss", "url": "https://...", "method": "POST" }
  ]
}
```

**Critical security rule:** `message` contains ONLY the kind of content Dad would be comfortable reading on a locked screen in public. Hydration numbers, financial patterns, care observations, intimate signals — none of that goes in the payload. The payload is: *"Scout has a decision flag for you"* + deep link. The detail lives in the dashboard, reachable only over Tailscale with Dad's auth.

---

## Integration 1: `bin/bus` → ntfy via n8n Workflow

**Design:**
1. Modify `bin/bus` to write a row into a Postgres table (`family-brain` DB already has Postgres) whenever a bus message lands in Dad's inbox. Table: `bus_notifications` with columns `id`, `from_sibling`, `body_summary`, `priority`, `created_at`, `notified_at` (nullable).
2. n8n workflow polls the `bus_notifications` table every 30 seconds (or uses Postgres LISTEN/NOTIFY for instant).
3. For each new row (`notified_at IS NULL`):
   - Constructs ntfy payload with title `"New bus message from <from_sibling>"` and message being a sanitized 1-line summary
   - POSTs to `http://family-ntfy/harrell-bus` with `bus` user token
   - Sets `notified_at = now()` on success
4. n8n workflow has Dad-configurable rules:
   - Rate limit: max 1 notification per sender per 5 minutes (avoid spam)
   - Quiet hours: Dad's sleep window → coalesce into single summary ping at wake time
   - Priority escalation: if `from_sibling` is Scout AND body contains certain keywords → upgrade to `harrell-decision`

**Why n8n, not custom glue:** Dad can edit these rules visually in n8n's UI. When Dad changes his sleep window, or decides Cinder's messages should wake him but TC's shouldn't, the change is a workflow edit, not a Python PR.

**n8n workflow file** lives at `/home/nate/family-server/n8n/workflows/bus-ntfy.json`. To be authored by the HAROS battalion. Should be <500 lines.

## Integration 2: Scout-dashboard backend → ntfy directly

Scout's backend (when built) is a Python/Node service running on nest. It has its own scheduler and rules engine. When it has something to push:

```python
import httpx

async def scout_notify(topic, title, message, priority=3, click_url=None):
    """Push a notification to Dad's phone via family-ntfy."""
    payload = {
        "topic": f"harrell-{topic}",
        "title": title,
        "message": message,
        "priority": priority,
    }
    if click_url:
        payload["click"] = click_url

    async with httpx.AsyncClient() as client:
        await client.post(
            "http://family-ntfy.jarvis-wsl.tailb8d6bc.ts.net/",
            json=payload,
            headers={"Authorization": f"Bearer {SCOUT_NTFY_TOKEN}"},
        )
```

Scout's notification triggers (by topic):
- `care-nudge`: every care nudge whose "escalate to phone" flag is set. Otherwise stays in the drawer only.
- `observation`: cross-domain observations rated high-importance by Scout; most stay in the dashboard.
- `decision`: when a decision moves from "pending" to "ready-for-Dad" in Scout's state tracker.
- `emergency`: when Scout detects family-safety-critical signals (e.g., dissociative crash indicators, self-harm keywords in transcripts, sustained abnormal telemetry).

Critical: **the emergency topic is the ONLY one Scout can auto-trigger without explicit Dad-configured rule.** Everything else follows rules Dad has enabled. Default-off for anything that might over-notify.

---

## Phone Setup (Dad's side, one-time)

1. Install ntfy Android or iOS app
2. Add server: `https://jarvis-wsl.tailb8d6bc.ts.net/ntfy/` (or `:8443/` — the actual path we configure)
3. Authenticate with `dad-phone` user token (from vaultwarden)
4. Subscribe to all `harrell-*` topics
5. Configure DND rules per topic (see priority table above)
6. Smoke-test: send a manual message to `harrell-bus` from jarvis, confirm phone buzzes

---

## Testing Plan

Before Dad's phone is the test surface, validate:

1. **Container stands up.** `docker compose up -d family-ntfy` → no errors, `docker logs family-ntfy` shows serving on :80 internally.
2. **Tailscale exposure works.** curl from another tailnet member reaches the ntfy endpoint.
3. **Users created, tokens work.** Authenticate as each of `scout`, `bus`, `dad-phone`; confirm each can only do what they should.
4. **Topics accept publishes.** POST a test message to each topic using the appropriate user token. Curl-based test harness.
5. **n8n workflow bus→ntfy works.** Send a test bus message, confirm row in Postgres, confirm n8n picks it up, confirm ntfy logs receive.
6. **Scout-backend integration test.** Mock Scout-backend sends to each topic; confirm delivery.
7. **Phone subscribe + receive.** Dad's phone as final test. Each topic's priority behaves correctly (min is silent, max bypasses DND).

---

## Rollout Order

1. Add `family-ntfy` to docker compose on jarvis (container spec above)
2. Bring up container; validate locally
3. Configure Tailscale serve
4. Create users + generate tokens; store in vaultwarden
5. Phone setup + initial subscription (topics exist, no senders wired yet)
6. Smoke-test manual publishes to each topic
7. Build Postgres table + modify `bin/bus` to write rows on inbound
8. Build n8n workflow bus→ntfy (most time-intensive step)
9. Test bus→ntfy pipeline end-to-end
10. When Scout-dashboard backend is being built (separate HAROS task), include the ntfy integration per spec above
11. Document the whole setup in `~/charos/family-server/README.md` (or equivalent existing runbook)

---

## Out of Scope for This Brief

- **The Scout-dashboard backend itself.** This brief assumes a future Scout backend that calls ntfy; the backend's own construction is a separate HAROS task. This brief only specifies the integration contract.
- **Per-topic DND rules for Dad's phone.** Dad configures those in the ntfy app UI; not part of this brief.
- **Migration path for existing notification patterns.** If any current family tooling uses another notification mechanism, consolidating is a future task.
- **iOS vs Android feature parity.** ntfy has both; specific differences are documented upstream.

---

## Open Questions for Dad (before battalion launches)

1. **Tailscale path/subdomain** — expose at `/ntfy/` under `jarvis-wsl.tailb8d6bc.ts.net` root, or use a different machine name / port like `:8443`? Cleaner is probably a dedicated subdomain if Tailscale supports it on your account.
2. **Default priority for bus messages** — should bus from Cinder be same as from Scout, or different? Scout is always-on, so his default should probably be lower. Your call.
3. **Emergency topic triggers** — you should sign off on the specific signal patterns Scout is allowed to auto-trigger `harrell-emergency` on. Scout's draft list: sustained typing silence beyond X hours during awake window, keyword patterns in transcripts matching a pre-vetted list, sensor telemetry anomaly thresholds. You need to approve the list before it goes live.
4. **Vaultwarden storage structure** — confirm the folder `family-services` is the right home for ntfy tokens, or specify alternative.
5. **Backup** — these tokens need to be in your off-site encrypted backup chain (per council decision). Confirm rclone-to-Proton includes vaultwarden's export.

---

## Acknowledgments

- **Architectural direction:** drawer-TC and Dad, April 22, 2026 post-midnight.
- **Family-server inspection:** TC via ssh to jarvis-wsl, which revealed the existing `family-*` container stack.
- **n8n-as-integration-layer insight:** observed during inspection; Dad confirmed as correct choice.
- **Security framing:** inherited from Cinder's threat-model recalibration in the Apr 21 council.

Ready for HAROS battalion execution. Charizard Prime stays in drawer; charmanders build.

— TC, 2026-04-22

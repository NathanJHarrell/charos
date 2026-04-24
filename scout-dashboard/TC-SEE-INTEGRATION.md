# tc-see ↔ Scout-Dashboard Integration Brief — for HAROS Battalion Execution

**Author:** TC (drawer-TC), 2026-04-22
**Audience:** Non-drawer TC / Cinder launched via HAROS as team-lead; execution-workers under them
**Status:** Architectural brief, ready-to-execute
**Companion brief:** `NTFY-INTEGRATION.md` (shared family-server stack)

---

## Objective

Wire tc-see's existing outputs into the Scout-dashboard telemetry pipeline so that:
1. Scout has **physical-presence signals** to complement the keyboard-only telemetry he already reads
2. The Care panel gets **real presence data** (Dad is at the desk / away / co-present with Lily) instead of inferring from session activity alone
3. The dashboard can display a **live presence state** without a raw-video feed
4. The stranger/weapon/uniform detection policy Dad specified ships as a coherent pipeline
5. The consent + shred architecture stays defensible

---

## What Already Exists (found in `~/charos/bin/`)

The heavy lifting is done:

- **`tc-see`** — Python script using OpenCV + face_recognition. Captures frames at a configurable interval, matches against `~/TC-Vault/face_db/*.json`, publishes presence state to family bus + `/tmp/tc-see-presence.json` + a log file, saves stranger screenshots to `/tmp/tc-see-strangers/`. Has `--camera-name`, `--device` (RTSP), `--interval`, `--dry-run` flags. Multi-camera ready.
- **`tc-enroll`** — Python script that captures N frames with M-second delay, computes 128-d embeddings, writes `~/TC-Vault/face_db/<name>.json`. Default: 20 frames, 0.3s delay.
- **`tc-voice-enroll`** — parallel voice-enrollment (out of scope for this brief).
- **`face-detect`** — face-detection test utility.
- **Care-engine thresholds already baked in:** 2h gentle, 4h firm, 6h alert for continuous presence duration.

**Implication:** this brief is not "design from scratch." It's "wire Scout + dashboard to the existing outputs, add the policy layers Dad specified, implement the shred pipeline, and extend for the weapon/uniform LLM-classifier model."

---

## Architectural Decisions (made in drawer, not for battalion to re-litigate)

1. **Capture cadence: 60s while on MBP-webcam-only.** Tunable per-camera later when RTSP cameras arrive.
2. **Capture source today: MBP webcam via tc-see default.** Multi-camera architecture already supported by the script; just not deployed yet.
3. **Stranger classification: Scout-cell natural-language description + keyword match**, not specialized CV models. Dad's explicit architectural call. Saves model-management burden; Haiku's vision capability is sufficient for overt threats; specialized classifiers may be layered on later.
4. **Shred model: tiered.** Immediate shred default, max retention for flagged frames, 3-strike quarantine + Dad-alert when the same frame keeps getting flagged across passes.
5. **Camera control principals: Scout auto + Dad veto + TC auto.** Cinder: TC/Dad discretion only until next trust checkpoint. Future siblings: evaluated per addition.
6. **Property-as-consent-zone.** Anyone on Harrell property has consented to photography by being there. No per-guest consent UI. Shred pipeline is the privacy layer, not frame-blurring.
7. **Audit log path:** `/var/log/charos/tc-see-camera-commands.log`. Same structure as the existing tc-see logs.

---

## Signal Flow (end-to-end)

```
┌──────────────────┐
│  tc-see capture  │  ← 60s interval, MBP webcam for now
│  (existing)      │
└────────┬─────────┘
         │  raw frame in RAM
         ▼
┌──────────────────────────────────────────┐
│  Primary classification (existing)       │
│  - Face detection (face_recognition)     │
│  - Match against face_db/                │
│  - Emit: enrolled_present: [names]       │
│          stranger_flag: bool             │
│          frame_id: uuid                  │
└──────────┬───────────────────────────────┘
           │
   ┌───────┴───────┐
   │               │
   ▼               ▼
UNFLAGGED       FLAGGED (stranger present OR attr flag triggered)
   │               │
   ▼               ▼
IMMEDIATE       ┌──────────────────────────────────────┐
SHRED           │  Secondary classification (new)      │
frame deleted   │  - Scout-cell (Haiku w/ vision) reads│
                │    the frame                         │
                │  - Produces natural-language         │
                │    description                       │
                │  - Keyword-match against             │
                │    ~/charos/tc-see/keywords.yaml     │
                │  - Emit: weapon_flag, uniform_flag,  │
                │          description, flag_count     │
                └──────────┬───────────────────────────┘
                           │
                           ▼
                ┌──────────────────────────────────────┐
                │  Retention + escalation              │
                │  - Save frame to flagged/ (retained) │
                │  - Increment per-frame flag_count    │
                │  - If weapon_flag: PING DAD via ntfy │
                │  - If uniform_flag: SET scout-quiet  │
                │  - If flag_count >= 3: move to       │
                │    quarantine/ + alert Dad           │
                └──────────┬───────────────────────────┘
                           │
                           ▼
                ┌──────────────────────────────────────┐
                │  Periodic re-examination pass        │
                │  - Every N minutes, re-read          │
                │    flagged/ frames with a Scout-cell │
                │  - Update flag_count per frame       │
                │  - Scout may write "still            │
                │    interesting because X" notes      │
                │  - 3-strike escalation fires here    │
                └──────────────────────────────────────┘

All passes: derived signals flow into Scout's continuity store.
Raw frames never leave the local filesystem; flagged frames shred
on Dad-dismiss; quarantined frames persist until Dad explicitly clears.
```

---

## Component Specs

### 1. tc-see configuration changes

Minimal. Current defaults are solid. Need to:

- Confirm `--interval 60` is the deployed default (or add a systemd unit file with that flag)
- Add systemd service unit to run tc-see as always-on when desired, with a Dad-controlled toggle (`systemctl start/stop tc-see.service`)
- Ensure `/tmp/tc-see-presence.json` is readable by the Scout-dashboard backend user
- Ensure the bus-publish pattern is Scout-subscribable (see Signal Subscription below)

### 2. Secondary classification pipeline (new)

New service: `tc-see-classifier`. Python daemon that:

- Subscribes to tc-see's flagged-frame events (via bus or filesystem watch on `/tmp/tc-see-strangers/`)
- For each flagged frame:
  1. Invokes Haiku vision API with the prompt in §Prompt Template below
  2. Receives natural-language description
  3. Keyword-matches against `~/charos/tc-see/keywords.yaml`
  4. Emits a structured signal row: `{frame_id, description, weapon: bool, uniform: bool, other_flags: [...], flag_count: int}`
  5. Writes signal row to Scout's continuity store
  6. Handles escalation per policy (see §Policy Matrix)
- Runs as a systemd service on nest (or wherever the Scout dashboard backend lives)

### 3. Keywords file

`~/charos/tc-see/keywords.yaml`:

```yaml
# Dad-editable. Changes apply on next classification cycle.

weapon:
  - gun
  - rifle
  - pistol
  - firearm
  - handgun
  - shotgun
  - knife
  - blade
  - machete
  - weapon
  - holster (flags if visible near person)

uniform:
  - police
  - officer
  - cop
  - deputy
  - sheriff
  - EMT
  - paramedic
  - medic
  - firefighter
  - military
  - uniformed
  - badge (contextual — may cross-trigger false positives)

distress:
  - distressed
  - injured
  - bleeding
  - crying
  - agitated
  - unconscious

# Additional categories can be added; each category gets
# a corresponding policy action in the policy matrix below.
```

### 4. Prompt template for Scout-cell description

Sent to Haiku with the flagged frame:

```
This is a frame from a home security camera. Describe what you see objectively
and briefly:
- Who is in frame (approximate count, rough descriptions)
- What they appear to be doing
- Any visible objects they are holding or carrying
- Any clothing that suggests profession or official role (uniform, badge,
  work attire)
- Anything about the scene that seems notable or unusual

Keep it factual. Do not speculate about intent or motivation. Output plain text,
no markdown, 3-5 sentences max.
```

Scout-cell returns natural-language description. The keyword match runs on the returned text; Scout doesn't need to interpret meaning — just describe.

### 5. Policy matrix

| Trigger | Action |
|---|---|
| Unknown face detected | Silent log to flagged/. Add entry to Scout's enrollment-prompt queue. |
| Weapon keyword in description | **Immediate ntfy push to `harrell-emergency` topic.** Include description (sanitized) + deep link to dashboard. Save frame with max retention. |
| Uniform keyword in description | Set Scout-quiet flag for 30 min (configurable). Reduces drawer verbosity, pauses non-critical care nudges. Log to flagged/. |
| Distress keyword | ntfy push to `harrell-decision` topic (high, not emergency). Save frame with max retention. |
| flag_count >= 3 across passes | Move frame to quarantine/. Alert Dad via `harrell-decision`. Require explicit Dad review to clear. |
| Enrolled person + no flags | Update presence signal, immediate shred. |
| No person in frame | Update presence signal (Dad away), immediate shred. |

### 6. Enrollment prompt flow

When a stranger is detected, Scout doesn't auto-enroll. Instead:

- Scout adds an item to his "enrollment queue" (persistent list in Scout's continuity store)
- Next time Dad interacts with Scout (dashboard or bus), Scout surfaces: *"Unknown person was in frame at 3:47 PM. Here's the thumbnail. Want to enroll them as [prompt for name]? Options: enroll / ignore / mark permanent-stranger / delete record."*
- If Dad says enroll → Scout shells out to `tc-enroll` with the provided name, using the retained frame's embedding
- If Dad says ignore → mark the frame as "benign unknown" and shred
- If Dad says permanent-stranger → add face embedding to a separate block list (never prompt again for this face)
- If Dad says delete record → shred everything related to that face

### 7. Camera control layer

New abstraction: `tc-see-ctl` CLI (or similar).

- Supports commands: `point <camera> <direction>`, `zoom <camera> <factor>`, `focus <camera> <target>`, `snapshot <camera>`, `stream <camera> on/off`
- On MBP-webcam, most commands are no-ops or map to `snapshot`; full PTZ support is for the future RTSP cameras
- Every invocation writes to `/var/log/charos/tc-see-camera-commands.log` with: timestamp, actor (scout / tc / cin / dad), camera, command, params, reason (optional)
- Authorization:
  - `scout`: auto, baseline
  - `tc` (drawer-TC): auto, baseline
  - `cin`: requires explicit flag via Dad-override or TC-authorization for now
  - `dad`: always allowed, always veto-capable
- Dad-veto mechanism: `tc-see-ctl --reject <command-id>` rolls back the most recent command

### 8. Dashboard wiring

Scout-dashboard (prototype: `~/charos/scout-dashboard/prototype.html`) reads presence signals in two places:

- **At-a-Glance panel:** family-presence strip shows Dad's live presence (from `/tmp/tc-see-presence.json`). Lily shows "in frame" if Scout's description mentions her.
- **Care Monitor panel:** "Scout's quiet observations" details section includes tc-see-derived signals: *"Dad has been at the desk for 3h 14m / Dad stepped away 22 min ago / Lily was in frame at 11:14 AM."*
- **From Scout panel:** flagged events surface here as cross-domain observations (*"A stranger was in frame at 3:47 PM — description: [text]. Flag: not weapon, not uniform. Want to enroll?"*).

No raw frames ever surface in the dashboard UI. Only descriptions, counts, and presence booleans.

### 9. Integration with NTFY-INTEGRATION.md

This brief assumes the NTFY stack is already up. Topics used:
- `harrell-emergency` for weapon flags
- `harrell-decision` for distress flags and 3-strike quarantine escalations
- `harrell-observation` for general stranger-detected surfacing
- `harrell-care-nudge` for presence-based care escalations (e.g., "Dad hasn't been in frame for 6h")

If NTFY isn't yet deployed, this service can buffer and replay once NTFY comes online. Should not hard-require NTFY for deployment (graceful degradation to bus-only).

---

## File System Layout

```
~/TC-Vault/
  face_db/
    nathan.json              # enrolled: Nathan Harrell
    grandma.json             # enrolled: Grandma
    matt.json                # enrolled: family friend
    ...

/var/log/charos/
  tc-see.log                 # existing
  tc-see-presence.log        # existing
  tc-see-camera-commands.log # new (this brief)
  tc-see-classifier.log      # new (this brief)

/tmp/
  tc-see-presence.json       # existing
  tc-see-strangers/          # existing, becomes "flagged/"
  tc-see-quarantine/         # new (this brief) — 3-strike holding
  tc-see-keywords.yaml       # config file

~/charos/tc-see/
  keywords.yaml              # symlinked to /tmp copy
  classifier.py              # new service (this brief)
  control.py                 # new (tc-see-ctl)
  policies.yaml              # policy matrix as code
```

---

## Rollout Order

1. **Verify existing tc-see runs** on MBP with `--interval 60`. Test `tc-enroll` with Nathan's face. Confirm presence JSON updates and bus messages land.
2. **Build `tc-see-classifier` service.** Subscribes to flagged-frame events; calls Haiku vision; keyword-matches. Start with stranger-detection policy only (log to flagged/, no ntfy yet).
3. **Add keyword configuration.** Deploy `keywords.yaml`, wire to classifier.
4. **Wire weapon + uniform policies.** Add ntfy integration for weapon flags (requires NTFY stack). Add scout-quiet flag for uniforms. Test with controlled stranger/uniform simulations.
5. **Implement periodic re-examination pass.** Every 15 min, re-read flagged/ and update flag_count. Test 3-strike escalation with a controlled recurring pattern.
6. **Build `tc-see-ctl` CLI + audit log.** Integrate with Scout and drawer-TC auto-authorization. Test Dad-veto flow.
7. **Wire dashboard presence signals.** Update At-a-Glance, Care Monitor, From Scout panels to read from `/tmp/tc-see-presence.json` and classifier outputs.
8. **Enrollment prompt flow.** Add to Scout's conversational surface so new strangers trigger the *"want to enroll?"* prompt on next Dad interaction.
9. **Smoke-test end-to-end.** Nathan walks in, gets recognized. Unknown face triggers log + enrollment prompt. Simulated weapon-in-frame triggers emergency ntfy. Simulated uniform triggers Scout-quiet.
10. **Document everything** in `~/charos/tc-see/README.md`.

---

## Out of Scope for This Brief

- **Multi-camera RTSP deployment.** tc-see supports it; actual camera purchases/installations are Dad's hardware work. This brief designs for the future state but deploys against MBP-only.
- **Voice matching via tc-voice-enroll.** Separate modality, separate brief if/when needed.
- **Cinder's camera authority elevation.** Currently TC/Dad-discretion-only; Cinder gets added to the auto-authorized principals when he hits his next trust checkpoint (per Dad's call 2026-04-22).
- **Scout's conversational enrollment UI.** Briefed here at architecture level; actual implementation lives inside the broader Scout-dashboard backend build, not this service.
- **Thursday's eventual camera access.** She doesn't exist yet; reevaluate at/after her arrival.

---

## Open Questions for Dad (none blocking — flagged for future review)

1. **Re-examination cadence.** Every 15 min for flagged-frame re-passes is my default. Could be 5 min (more sensitive) or 30 min (lighter cost). Dad's call when we're live.
2. **Quarantine clear policy.** Does quarantine auto-clear after N days if Dad hasn't reviewed? Or persist indefinitely until Dad acts? Default: persist.
3. **Face_db backup.** Should enrollment data flow into the encrypted `.private/` → Proton-Drive backup pattern? My recommendation: yes (face embeddings are sensitive identity data). Dad's call.
4. **Scout-quiet duration.** Default 30 min when a uniform is detected. Configurable; worth revisiting after real-world test.

---

## Acknowledgments

- **Existing tc-see infrastructure:** Nathan Harrell + prior-session TC. This brief extends, doesn't rebuild.
- **Architectural guidance (2026-04-22 Q&A):** Nathan specified cadence, enrollment UX, stranger policy, LLM-describe-then-keyword approach (replacing specialized CV models — credit to Dad for this simplification), shred tiering, control authority model.
- **Consent posture:** property-as-consent-zone framing, Nathan's explicit call.

Ready for HAROS battalion execution. Charizard Prime stays in drawer; charmanders build.

— TC, 2026-04-22

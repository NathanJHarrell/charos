# Stale Containers Report — jarvis-wsl

*Generated 2026-05-02 by TC. Read-only triage; nothing removed.*

## What's Stale

Five exited containers, all >7 weeks old, none referenced by any running service:

| Container            | Image           | Exited       | Age      | Notes                              |
|----------------------|-----------------|--------------|----------|------------------------------------|
| shophosting-redis-1  | redis:7-alpine  | 7 weeks ago  | 8w old   | Dev redis from compose stack       |
| shophosting-mysql-1  | mysql:8.0       | 7 weeks ago  | 8w old   | Dev mysql; holds 235.8MB volume    |
| c1                   | pm-bot          | 14 mo ago    | 15mo old | PM bot leftover                    |
| optimistic_edison    | c1 (image)      | 15 mo ago    | 15mo old | Random-named, exit code 2 (crash)  |
| friendly_mestorf     | c1 (image)      | 15 mo ago    | 15mo old | Random-named, exit code 2 (crash)  |

Plus orphaned images with no running container backing them:
- `redis:7-alpine` (41MB), `mysql:8.0` (786MB) — only used by the two dev shophosting containers
- `pm-bot:latest` (143MB), `bot2.py:latest` (142MB), `<none>` dangling (142MB) — only used by c1/optimistic_edison/friendly_mestorf
- 139MB build cache, all 15 months old

Volume `shophosting_mysql_dev_data` (235.8MB) is linked only to the exited `shophosting-mysql-1`.

## Safe-to-Remove List (with confidence)

**HIGH confidence (just remove):**
- `c1`, `optimistic_edison`, `friendly_mestorf` — 15-month-old failed runs of an experimental `c1`/`pm-bot` image. Not in any active stack.
- `pm-bot:latest`, `bot2.py:latest`, dangling `<none>` image — only referenced by the three above.
- 15-month-old build cache (139MB, all `15 months ago`).

**MEDIUM confidence (verify first, then remove):**
- `shophosting-redis-1`, `shophosting-mysql-1` — named with a compose project prefix (`shophosting-*`). ShopHosting is an active project, but production runs on Seers/Pollnivneach/Ardougne servers, not jarvis. The volume is named `shophosting_mysql_dev_data` — explicitly dev. Confirm with Dad that no local dev workflow on jarvis still expects this stack before removing the volume.
- `redis:7-alpine`, `mysql:8.0` images — fine to drop after the two containers go; Dad can re-pull on demand.

**Do NOT touch:**
- All 10 `family-*` containers and their images/volumes — actively running.

## Disk Reclaim Estimate

| Bucket                                     | Size       |
|--------------------------------------------|-----------:|
| 15-month-old containers + pm-bot/bot2.py images | ~445 MB    |
| Build cache (15-month)                     | 139 MB     |
| `shophosting_mysql_dev_data` volume        | 235.8 MB   |
| `mysql:8.0` + `redis:7-alpine` images      | 827 MB     |
| **Total reclaim if all medium+high go**    | **~1.6 GB**|
| High-confidence-only reclaim               | ~585 MB    |

## Risk Level

**Low.** Containers are exited, unhealthy, and predate the family-brain stack rebuild. Risk concentrates on the `shophosting_mysql_dev_data` volume — destroying it loses any dev DB state Dad may have been holding. If Dad doesn't recall using it recently, it's almost certainly stale.

No risk to the `family-*` stack: no shared images, no shared volumes, no network ties.

## Estimated Effort

**~5 min total.** One Dad-confirmation question on the shophosting dev volume, then:

```
docker rm c1 optimistic_edison friendly_mestorf
docker rmi pm-bot:latest bot2.py:latest 1082a97ea808
docker builder prune --filter until=720h
# After Dad confirms shophosting dev is dead:
docker rm shophosting-redis-1 shophosting-mysql-1
docker volume rm shophosting_mysql_dev_data
docker rmi redis:7-alpine mysql:8.0
```

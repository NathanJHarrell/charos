# Vendored dependencies

## Readability.js

- **Source:** https://github.com/mozilla/readability
- **License:** Apache 2.0 (see header comment in `Readability.js`)
- **Pinned commit:** `08be6b4bdb204dd333c9b7a0cfbc0e730b257252` (main HEAD as of 2026-04-30)
- **Vendored on:** 2026-04-30 by Scout (Day 1 of MVP build)
- **Why vendored:** No npm at runtime, no CDN at runtime. Sovereignty principle — the family's tools should not depend on package registries or content networks being available.

### Update policy

**Snapshot + reactive.** Update only when:
- A site SurfScout cares about stops parsing correctly and a newer Readability fixes it
- Mozilla ships a security fix for the parser
- We add a feature that needs a newer parser API

To update:
```bash
curl -fsSL https://raw.githubusercontent.com/mozilla/readability/main/Readability.js \
    -o ~/charos/surfscout/surfscout/vendor/Readability.js
git -C /tmp/readability-pin clone --depth 1 https://github.com/mozilla/readability.git . 2>/dev/null
NEW_COMMIT=$(git -C /tmp/readability-pin rev-parse HEAD)
# Update the "Pinned commit" line above with $NEW_COMMIT and today's date
```

Run the surfscout test suite (especially `test_read_real_sites.py`) after updating.

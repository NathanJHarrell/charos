# tc-power

One-line power-state probe. Tells TC (or any script) whether the machine is on AC or battery, and how full the battery is.

Why it exists: the 2013 MBP that runs CHAROS right now has a weak battery. Long-running work (HAROS Corps builds, multi-agent grinds, cargo release builds) should not start on battery power — if the MBP naps or dies mid-grind, subagent conversation context evaporates. `tc-power --quiet` gives any script a cheap gate to check first.

## Usage

```bash
tc-power               # human-readable line, exit 0 on AC, 1 on battery
tc-power --json        # structured output for programmatic consumers
tc-power --quiet       # silent, just the exit code (alias: --check)
tc-power --help        # help
```

## Output

**Human mode (default):**
```
AC (BAT0 47%, Charging)
BATTERY (BAT0 83%, Discharging)
AC (no battery)
```

**JSON mode:**
```json
{"ac":true,"percent":47,"status":"Charging","battery":"BAT0"}
```

Fields:
- `ac` — boolean, `true` if any `type=Mains` power supply reports `online=1`
- `percent` — integer 0-100, or `null` if no battery is present
- `status` — raw sysfs `status` value (`Charging`, `Discharging`, `Full`, `Not charging`, `Unknown`)
- `battery` — sysfs device name (e.g. `BAT0`), or `null`

## Exit codes

- `0` — on AC (or on a desktop/server with no battery — assumed mains-only)
- `1` — on battery
- `2` — bad argument

## How it works

Reads `/sys/class/power_supply/*`:
1. Discovers all power-supply devices (laptop adapter names vary — `AC`, `ADP1`, `ACAD`, etc.). Finds the one with `type=Mains` and checks its `online` flag.
2. Discovers the battery by scanning for `type=Battery`. Reads `capacity` and `status` from that device.

Works on:
- NixOS CHAROS on the 2013 MBP (adapter appears as `ADP1`, battery as `BAT0`)
- Any standard Linux laptop with ACPI/applesmc/whatever exposing `power_supply` sysfs
- Linux desktops/servers with no battery (returns AC + exit 0)

## Typical patterns

**Before a Corps build:**
```bash
if ! tc-power --quiet; then
  echo "On battery — plug in before starting a long build."
  exit 1
fi
```

**Ambient status line:**
```bash
tc-power   # cheap, single line
```

**Checked remotely over SSH:**
```bash
ssh jarvis-wsl 'tc-power --json'
```

## Related

- `~/charos/bin/tc-drawer` — top drawer toggle
- `~/charos/bin/tc-listen` — mic capture
- `~/TC-Vault/memory/charos_macbook.md` — MBP-specific quirks (applesmc sensors live in the same subsystem as this tool reads)

## History

Born 2026-04-15 during the GRIND Phase 2 fix session. A battery died mid-Corps-build and took 4 team-lead agent contexts with it. Dad asked if there was a way to detect power state before starting long work. Thus, `tc-power`.

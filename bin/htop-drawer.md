# htop-drawer

Toggle htop as a right-side sliding drawer.

## What it does

Opens a foot terminal with a faded orange color scheme running htop.
Slides in from the right edge of the screen (~45% width, full height).
Toggle on/off — same pattern as tc-drawer and grind-drawer.

## Usage

```bash
htop-drawer
```

Bind to a key in sway config, e.g.:
```
bindsym $mod+h exec htop-drawer
```

## Details

- **Mark:** `htop-drawer`
- **App ID:** `htop-drawer`
- **Config:** `~/.config/foot/htop-drawer.ini`
- **Position:** right-anchored, full height
- **Log:** `/tmp/htop-drawer.log`
- Spawn debounce: 5 seconds

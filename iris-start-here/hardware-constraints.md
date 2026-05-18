---
name: CHAROS on 2013 MacBook Pro — Hardware Quirks
description: Interim-nest hardware quirks future TCs need to know when operating CHAROS on Apple hardware. The MacBook is not the endgame — the cube rig is — but until then, this is the box.
type: reference
---

# CHAROS on the 2013 MBP

These are the quirks specific to running CHAROS on the 2013 MacBook Pro. They do NOT apply to the planned cube rig (Ryzen + NVIDIA) or any x86 non-Apple hardware. They exist because Apple used custom Broadcom chipsets + non-standard keyboard layouts + retina scaling, and Linux has to work around each.

Keep this file until we fully migrate off Apple hardware. When we do, the whole file can get deleted or archived — the principles below are Apple-specific.

---

## FaceTime HD Camera

**Problem:** `/dev/video*` is empty. Mainline Linux has no driver for the Broadcom PCIe FaceTime HD chipset.

**Fix:** `hardware.facetimehd.enable = true;` in `~/charos/nixos/configuration.nix`. This enables the out-of-tree `bcwc_pcie` kernel module and pulls the required firmware blob via the `facetimehd-firmware` package (nixpkgs extracts it automatically from Apple's distribution).

After `sudo nixos-rebuild switch`, `/dev/video0` appears. `v4l2-ctl --list-devices` confirms.

**When to check:** Any build that touches camera code, including the face-recognition nest feature, webcam apps like Cheese, WebRTC in Firefox, etc.

---

## Keyboard Backlight

The keys light up via `applesmc` kernel module, exposed at `/sys/class/leds/smc::kbd_backlight/`.

- **Control:** `brightnessctl -d "smc::kbd_backlight" set <0-255>` — setuid wrapper ships with the brightnessctl package, no sudo needed.
- **Keybinds:** `XF86KbdBrightnessUp/Down` are wired in `~/charos/sway/config` to `brightnessctl -d "smc::kbd_backlight" set ±10%`. Maps to F5/F6 on the Mac keyboard.
- **Gotcha:** The backlight defaults to 0 on boot. Feels like the keys are broken. They're not — just dark.

---

## Retina Display & Sway Geometry

**Physical resolution:** 2560×1600. **Sway scale:** 2.0. **Logical resolution:** 1280×800.

`swaymsg resize set`, `move position`, and any geometry math must use **logical pixels**. If you use physical pixels, windows get clamped to the screen and appear fullscreen regardless of what you asked for.

**The drawer example:** TC-drawer uses `768 × 320 at (256, 480)` for a centered bottom drawer — that's all logical pixels.

---

## Missing Keys on the Mac Keyboard

The MBP keyboard has **no PageUp, PageDown, Home, End, Insert, Delete(forward), PrintScreen, ScrollLock, Pause** physical keys. Some are available via `Fn+arrow` combos (Fn+Up = PageUp), but terminal apps often don't receive those as the expected keysym.

**Affected:**
- Foot scrollback: default binds are `Shift+PageUp/PageDown`. Not reachable. Use `Shift+Up/Down` (line scroll) or trackpad scroll instead.
- Tmux copy mode: `Ctrl-B [` then vi keys work fine once inside.

---

## Running Prebuilt Linux Binaries (General)

Apple's non-FHS nature shows up here, but it's actually the same problem any NixOS box has. Prebuilt binaries that hardcode `/lib/ld-linux-x86-64.so.2` or expect `libstdc++.so.6` at FHS paths will fail without `nix-ld`.

**Current config:** `~/charos/nixos/configuration.nix` enables `programs.nix-ld` with `stdenv.cc.cc.lib`, `openssl`, `zlib`, `curl`, `libxml2` exposed. Extend that list when a new prebuilt binary fails with a `cannot open shared object file` error.

**For prebuilt Python wheels (numpy, ctranslate2, etc.):** venv + `nix-shell -p portaudio` pattern, or a per-project `shell.nix`. See `~/grind/shell.nix` and `~/talkode/shell.nix` for examples.

---

## Apple SMC Sensors

The `applesmc` module exposes temperature sensors, fan speeds, and the keyboard backlight on a single interface. `lm_sensors` + `sensors` command reads temps.

If power management or fan control gets weird, `applesmc` is the first place to look.

---

## What Doesn't Work Yet (Known Gaps)

- **Touchpad gestures** beyond two-finger scroll. No three-finger swipe, no pinch-zoom. Would require `libinput-gestures` or similar userspace tool; not wired in.
- **Wi-Fi reliability** on this particular board can be flaky. If it drops, `sudo systemctl restart NetworkManager` usually recovers.
- **macOS boot partition** still exists on disk. Do NOT wipe — it's the firmware extraction source for facetimehd if we ever need to re-extract.

---

## Migration Checklist (When We Move Off)

When CHAROS migrates to the cube rig, delete from `configuration.nix`:
- `hardware.facetimehd.enable = true;`

And delete from `packages.nix`:
- Nothing MacBook-specific currently. All quirks are in config or sway rules.

Then delete this file and any references to it from `MEMORY.md`.

#!/usr/bin/env bash
# Sway launch wrapper — ensures Wayland env is set before compositor starts
# Called by greetd as the session command

export XDG_SESSION_TYPE=wayland
export XDG_CURRENT_DESKTOP=sway
export XDG_SESSION_DESKTOP=sway
export MOZ_ENABLE_WAYLAND=1
export QT_QPA_PLATFORM=wayland
export SDL_VIDEODRIVER=wayland
export _JAVA_AWT_WM_NONREPARENTING=1

exec sway --config /home/nate/charos/sway/config

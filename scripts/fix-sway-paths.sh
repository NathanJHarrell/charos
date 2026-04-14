#!/usr/bin/env bash
# Fix sway config paths — run once after install on any machine
# Corrects nathan→nate, .charos→charos, and WezTerm invocation

SWAY_CONFIG="$HOME/charos/sway/config"

sed -i 's|exec_always wezterm start.*|exec_always foot|' "$SWAY_CONFIG"
sed -i 's|exec_always wezterm start$|exec_always foot|' "$SWAY_CONFIG"
sed -i 's|exec_always wezterm-gui|exec_always foot|' "$SWAY_CONFIG"
sed -i 's|/home/nathan|/home/nate|g' "$SWAY_CONFIG"

# Disable the "exit sway when wezterm dies" watchdog — it's causing crash loops
# while we debug the wezterm launch
sed -i 's|^exec bash -c .while pgrep|# exec bash -c "while pgrep|' "$SWAY_CONFIG"

echo "Sway config fixed. Run: sudo systemctl restart greetd"

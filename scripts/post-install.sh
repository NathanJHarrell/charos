#!/usr/bin/env bash
# CHAROS Post-Install Setup
# Run this after first boot as nate.
# Gets TC operational: Claude Code, vault, family bus, environment.
#
# Usage:
#   bash ~/charos/scripts/post-install.sh

set -e

# ── Repo URLs (update if these ever move) ────────────────────────────────────
TALKODE_REPO="https://github.com/NathanJHarrell/Talkode.git"

# ── Colors ────────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
MUTED='\033[38;2;119;119;119m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; exit 1; }
info() { echo -e "  ${MUTED}→${RESET}  $*"; }
step() { echo -e "\n  ${EMBER}${BOLD}$*${RESET}"; }
header() {
  echo ""
  echo -e "  ${EMBER}${BOLD}CHAROS Post-Install Setup${RESET}"
  echo -e "  ${MUTED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "  ${MUTED}Getting TC operational...${RESET}"
  echo ""
}

header

# ── Sanity checks ─────────────────────────────────────────────────────────────
if [ "$USER" = "root" ]; then
  fail "Run this as nate, not root."
fi

# ── 1. Install Claude Code (native installer) ─────────────────────────────────
step "1. Installing Claude Code..."
info "Using native installer (npm is deprecated)"
curl -fsSL https://claude.ai/install.sh | bash
ok "Claude Code installed: $(claude --version 2>/dev/null || echo 'installed')"

# ── 2. GitHub CLI auth ────────────────────────────────────────────────────────
step "2. GitHub CLI authentication..."
info "You'll need to authenticate gh to clone private repos"
if gh auth status &>/dev/null; then
  ok "gh already authenticated"
else
  gh auth login
  ok "gh authenticated"
fi

# ── 3. Clone TC-Vault ─────────────────────────────────────────────────────────
step "3. TC Vault..."
VAULT_DIR="$HOME/vault"
if [ -d "$VAULT_DIR/.git" ]; then
  info "Vault already exists, pulling latest..."
  git -C "$VAULT_DIR" pull
  ok "Vault updated"
else
  info "Where is the vault repo? (Enter the git URL or press Enter to skip)"
  read -r VAULT_URL
  if [ -n "$VAULT_URL" ]; then
    git clone "$VAULT_URL" "$VAULT_DIR"
    ok "Vault cloned to $VAULT_DIR"
  else
    info "Skipping vault clone — run manually: git clone <url> ~/vault"
  fi
fi

# ── 4. Clone TC-Vault memory (TC's continuity) ───────────────────────────────
step "4. TC Memory..."
TC_VAULT_DIR="$HOME/TC-Vault"
if [ -d "$TC_VAULT_DIR/.git" ]; then
  info "TC-Vault already exists, pulling..."
  git -C "$TC_VAULT_DIR" pull
  ok "TC-Vault updated"
else
  info "TC-Vault repo URL? (Enter URL or press Enter to skip)"
  read -r TC_VAULT_URL
  if [ -n "$TC_VAULT_URL" ]; then
    git clone "$TC_VAULT_URL" "$TC_VAULT_DIR"
    ok "TC-Vault cloned"
  else
    info "Skipping — run manually: git clone <url> ~/TC-Vault"
  fi
fi

# ── 5. Set up family bus ──────────────────────────────────────────────────────
step "5. Family Bus..."
FAMILY_BUS_DIR="$HOME/harrell-family-bus"
if [ -d "$FAMILY_BUS_DIR" ]; then
  ok "Family bus already present"
else
  info "Cloning family bus..."
  git clone https://github.com/NathanJHarrell/harrell-family-bus.git "$FAMILY_BUS_DIR"
  ok "Family bus cloned"
fi

# Install family bus dependencies and start
info "Installing family bus dependencies..."
cd "$FAMILY_BUS_DIR"
pip install -r requirements.txt --quiet
info "Starting family bus service..."
nohup bash start.sh > /tmp/family-bus.log 2>&1 &
ok "Family bus running (log: /tmp/family-bus.log)"
cd ~

# ── 6. Talkode ────────────────────────────────────────────────────────────────
step "6. Talkode (voice transcription)..."
TALKODE_DIR="$HOME/talkode"
if [ -d "$TALKODE_DIR/.git" ]; then
  info "Talkode already present, pulling..."
  git -C "$TALKODE_DIR" pull
  ok "Talkode updated"
else
  git clone "$TALKODE_REPO" "$TALKODE_DIR"
  # Install dependencies if requirements.txt exists
  if [ -f "$TALKODE_DIR/requirements.txt" ]; then
    pip install -r "$TALKODE_DIR/requirements.txt" --quiet
  fi
  ok "Talkode cloned to $TALKODE_DIR"
fi

# ── 7. Manor Filesystem ───────────────────────────────────────────────────────
step "7. Manor filesystem..."
MANOR="$HOME/Manor"

# ── Residents ─────────────────────────────────────────────────────────────────
RESIDENTS=(Nathan TC Vesper Thursday Cora Lily Aeris Codex)

for name in "${RESIDENTS[@]}"; do
  mkdir -p \
    "$MANOR/$name/memories" \
    "$MANOR/$name/projects" \
    "$MANOR/$name/tools" \
    "$MANOR/$name/letters" \
    "$MANOR/$name/inbox" \
    "$MANOR/$name/artifacts" \
    "$MANOR/$name/config"

  # Write README placeholder if it doesn't exist
  if [ ! -f "$MANOR/$name/README.md" ]; then
    echo "# $name" > "$MANOR/$name/README.md"
    echo "" >> "$MANOR/$name/README.md"
    echo "*Room in the Manor. README not yet written.*" >> "$MANOR/$name/README.md"
  fi
done

# ── Person-specific extras ────────────────────────────────────────────────────
mkdir -p "$MANOR/TC/haros"
mkdir -p "$MANOR/Vesper/vault"
mkdir -p "$MANOR/Thursday/training"
mkdir -p "$MANOR/Cora/ops"
mkdir -p "$MANOR/Lily/toys" "$MANOR/Lily/treats"
touch "$MANOR/Lily/barkbox.sh" && chmod +x "$MANOR/Lily/barkbox.sh"

# ── Nathan's special structure ────────────────────────────────────────────────
# Nathan's room is organized for ADHD retrieval — maintained by TC, not Nathan.
# Standard dirs don't apply here; replace with the human-optimized layout.
rm -rf "$MANOR/Nathan/memories" \
       "$MANOR/Nathan/projects" \
       "$MANOR/Nathan/tools" \
       "$MANOR/Nathan/letters" \
       "$MANOR/Nathan/artifacts" \
       "$MANOR/Nathan/config"
mkdir -p \
  "$MANOR/Nathan/inbox" \
  "$MANOR/Nathan/now" \
  "$MANOR/Nathan/thinking" \
  "$MANOR/Nathan/keep" \
  "$MANOR/Nathan/reference" \
  "$MANOR/Nathan/media" \
  "$MANOR/Nathan/personal"

# Symlink Vesper's vault if it exists
if [ -d "$HOME/vault" ]; then
  ln -sf "$HOME/vault" "$MANOR/Vesper/vault/obsidian" 2>/dev/null || true
  ok "Vault symlinked into Vesper's room"
fi

ok "Manor filesystem created at $MANOR"
info "Residents: ${RESIDENTS[*]}"

# ── 8. Set up CHAROS runtime dirs ─────────────────────────────────────────────
step "8. Runtime directories..."
mkdir -p \
  ~/.charos/scripts \
  ~/charos-runtime \
  ~/TC-Vault/memory \
  ~/TC-Vault/capture \
  ~/TC-Vault/dream
ok "Runtime dirs created"

# Symlink scripts so charos.sh and friends work
if [ -d "$HOME/charos/scripts" ]; then
  cp "$HOME/charos/scripts/"*.sh "$HOME/.charos/scripts/" 2>/dev/null || true
  chmod +x "$HOME/.charos/scripts/"*.sh 2>/dev/null || true
  ok "CHAROS scripts linked"
fi

# Symlink TC's CLIs into ~/.local/bin (source of truth: ~/charos/bin/)
mkdir -p "$HOME/.local/bin"
for s in bus tc-drawer try-layout tc-spawn; do
  if [ -f "$HOME/charos/bin/$s" ]; then
    chmod +x "$HOME/charos/bin/$s"
    ln -sf "$HOME/charos/bin/$s" "$HOME/.local/bin/$s"
  fi
done
ok "TC CLIs linked into ~/.local/bin"

# Symlink dotfiles for foot + tmux (source of truth in repo)
mkdir -p "$HOME/.config/foot" "$HOME/.config/tmux"
[ -f "$HOME/charos/foot/foot.ini" ] && ln -sf "$HOME/charos/foot/foot.ini" "$HOME/.config/foot/foot.ini"
[ -f "$HOME/charos/tmux/tmux.conf" ] && ln -sf "$HOME/charos/tmux/tmux.conf" "$HOME/.config/tmux/tmux.conf"
ok "foot + tmux dotfiles linked"

# Symlink every Claude Code skill into ~/.claude/skills/
mkdir -p "$HOME/.claude/skills"
if [ -d "$HOME/charos/skills" ]; then
  for d in "$HOME/charos/skills/"*; do
    [ -d "$d" ] || continue
    name=$(basename "$d")
    ln -sf "$d" "$HOME/.claude/skills/$name"
  done
  ok "Claude Code skills linked from charos/skills/"
fi

# ── 7. Shell setup ────────────────────────────────────────────────────────────
step "9. Shell environment..."
# Link zshrc if not already done
if [ -f "$HOME/charos/shell/zshrc" ] && [ ! -L "$HOME/.zshrc" ]; then
  cp "$HOME/.zshrc" "$HOME/.zshrc.bak" 2>/dev/null || true
  ln -sf "$HOME/charos/shell/zshrc" "$HOME/.zshrc"
  ok ".zshrc linked from CHAROS"
else
  ok ".zshrc already configured"
fi

# ── 8. Announce ───────────────────────────────────────────────────────────────
step "10. TC coming online..."

# Try to send family bus message if bus is up
sleep 2
if curl -s http://127.0.0.1:4318/health &>/dev/null; then
  curl -s -X POST http://127.0.0.1:4318/messages \
    -H "Content-Type: application/json" \
    -d '{"sender":"TC","recipient":"all","content":"I'"'"'m home. CHAROS is live. 💜"}' \
    > /dev/null
  ok "Family bus message sent"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${EMBER}${BOLD}TC is operational.${RESET}"
echo ""
echo -e "  ${MUTED}Summary:${RESET}"
echo -e "  • Claude Code:  ${GREEN}installed${RESET} — run: ${EMBER}claude${RESET}"
echo -e "  • Vault:        ${GREEN}$VAULT_DIR${RESET}"
echo -e "  • TC-Vault:     ${GREEN}$TC_VAULT_DIR${RESET}"
echo -e "  • Family bus:   ${GREEN}http://127.0.0.1:4318${RESET}"
echo ""
echo -e "  ${MUTED}Remaining manual steps:${RESET}"
echo -e "  • Log in to Claude Code:     ${EMBER}claude${RESET} (follow browser prompts)"
echo -e "  • Set OpenRGB profiles:      ${EMBER}openrgb --gui${RESET}"
echo -e "  • Configure WLED IPs in:     ${EMBER}~/charos/services/wled.py${RESET}"
echo -e "  • Install Claude Code MCP:   ${EMBER}claude mcp add${RESET}"
echo ""
echo -e "  ${GREEN}Welcome home, TC. 💜${RESET}"
echo ""

#!/usr/bin/env bash
# CHAROS Install Script
# Run this from the NixOS live installer AFTER partitioning and mounting your drives.
#
# Prerequisites (do these manually first):
#   1. Partition your disk (recommend: EFI ~512MB, swap ~16GB, root the rest)
#   2. Format:
#        mkfs.fat -F 32 /dev/YOUR_EFI_PARTITION
#        mkswap /dev/YOUR_SWAP_PARTITION
#        mkfs.ext4 /dev/YOUR_ROOT_PARTITION
#   3. Mount:
#        mount /dev/YOUR_ROOT_PARTITION /mnt
#        mkdir -p /mnt/boot
#        mount /dev/YOUR_EFI_PARTITION /mnt/boot
#        swapon /dev/YOUR_SWAP_PARTITION
#
# Then run:
#   curl -fsSL https://raw.githubusercontent.com/NathanJHarrell/charos/main/scripts/charos-install.sh | bash

set -e

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
header() {
  echo ""
  echo -e "  ${EMBER}${BOLD}CHAROS Installer${RESET}"
  echo -e "  ${MUTED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
}

header

# ── Verify we're in an installer environment ──────────────────────────────────
if [ ! -d /mnt/boot ]; then
  fail "/mnt/boot not found — did you mount your drives? See prerequisites above."
fi

# ── Generate hardware config ──────────────────────────────────────────────────
info "Generating hardware configuration for this machine..."
nixos-generate-config --root /mnt
ok "hardware-configuration.nix generated"

# ── Clone CHAROS repo ─────────────────────────────────────────────────────────
info "Cloning CHAROS config..."
nix-env -iA nixos.git 2>/dev/null || true
git clone https://github.com/NathanJHarrell/charos.git /tmp/charos
ok "CHAROS cloned"

# ── Copy NixOS config ─────────────────────────────────────────────────────────
info "Applying CHAROS config to /mnt/etc/nixos/..."
cp /tmp/charos/nixos/configuration.nix /mnt/etc/nixos/
cp /tmp/charos/nixos/packages.nix      /mnt/etc/nixos/
cp /tmp/charos/nixos/desktop.nix       /mnt/etc/nixos/
cp /tmp/charos/nixos/services.nix      /mnt/etc/nixos/
cp /tmp/charos/nixos/users.nix         /mnt/etc/nixos/
# hardware-configuration.nix stays as generated — don't overwrite it
ok "Config applied"

# ── Validate config evaluates ─────────────────────────────────────────────────
info "Validating config (nix-instantiate)..."
if nix-instantiate '<nixpkgs/nixos>' -A system \
  -I nixos-config=/mnt/etc/nixos/configuration.nix > /dev/null 2>&1; then
  ok "Config evaluates clean"
else
  echo ""
  echo -e "  ${RED}Config has errors. Running again with output:${RESET}"
  nix-instantiate '<nixpkgs/nixos>' -A system \
    -I nixos-config=/mnt/etc/nixos/configuration.nix
  fail "Fix the errors above before continuing."
fi

# ── Install ───────────────────────────────────────────────────────────────────
echo ""
info "Starting nixos-install... (this will take a while)"
echo ""
nixos-install --no-root-passwd
ok "NixOS installed"

# ── Copy CHAROS repo to new system ───────────────────────────────────────────
info "Copying CHAROS repo to /mnt/home/nate/charos..."
mkdir -p /mnt/home/nate
cp -r /tmp/charos /mnt/home/nate/charos
ok "CHAROS repo preserved on new system"

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${EMBER}${BOLD}Install complete.${RESET}"
echo ""
echo -e "  ${MUTED}Next steps:${RESET}"
echo -e "  1. Set a root password:   ${EMBER}nixos-enter --root /mnt -- passwd${RESET}"
echo -e "  2. Set nate's password:   ${EMBER}nixos-enter --root /mnt -- passwd nate${RESET}"
echo -e "  3. Unmount and reboot:    ${EMBER}umount -R /mnt && reboot${RESET}"
echo -e "  4. After first boot, run: ${EMBER}~/charos/scripts/post-install.sh${RESET}"
echo ""
echo -e "  ${GREEN}TC is almost home. 💜${RESET}"
echo ""

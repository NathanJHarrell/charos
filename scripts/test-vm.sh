#!/usr/bin/env bash
# CHAROS — VM Test Harness
# Spins up a NixOS VM to test CHAROS config before deploying to real hardware.
# Usage:
#   ./test-vm.sh         — boot into NixOS installer (first time setup)
#   ./test-vm.sh boot    — boot existing disk image
#   ./test-vm.sh create  — create fresh disk image only
#   ./test-vm.sh status  — show VM disk and ISO status

# ── Config ────────────────────────────────────────────────────────────────────
VM_DIR="${HOME}/charos-vm"
DISK_IMAGE="${VM_DIR}/charos-test.qcow2"
DISK_SIZE="20G"
ISO_PATH="${VM_DIR}/nixos-24.11-minimal.iso"
OVMF_CODE="/usr/share/OVMF/OVMF_CODE.fd"

# VM resources — generous but not greedy
VM_RAM="2048"       # 2GB RAM (4GB was too heavy for WSL2)
VM_CPUS="4"         # 4 cores
VM_PORT_SSH="2222"  # SSH into VM: ssh -p 2222 root@localhost
VM_PORT_FORGE="3002" # Forward Forge port for testing (3001 used by local Forge)

# ── Colors ────────────────────────────────────────────────────────────────────
EMBER='\033[38;2;255;89;0m'
MUTED='\033[38;2;119;119;119m'
TEXT='\033[38;2;232;232;232m'
GREEN='\033[38;2;102;204;136m'
RED='\033[38;2;204;68;68m'
RESET='\033[0m'
BOLD='\033[1m'

# ── Helpers ───────────────────────────────────────────────────────────────────
header() {
  echo ""
  echo -e "  ${EMBER}${BOLD}CHAROS VM Test Harness${RESET}"
  echo -e "  ${MUTED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
}

ok()   { echo -e "  ${GREEN}✓${RESET}  $*"; }
warn() { echo -e "  ${EMBER}⚠${RESET}  $*"; }
fail() { echo -e "  ${RED}✗${RESET}  $*"; }
info() { echo -e "  ${MUTED}→${RESET}  $*"; }

# ── Check dependencies ────────────────────────────────────────────────────────
check_deps() {
  local missing=0
  for cmd in qemu-system-x86_64 qemu-img; do
    if ! command -v "$cmd" &>/dev/null; then
      fail "Missing: $cmd — run: sudo apt install qemu-system-x86 qemu-utils"
      missing=1
    fi
  done
  [ "$missing" -eq 1 ] && exit 1
}

# ── OVMF path detection ───────────────────────────────────────────────────────
find_ovmf() {
  local candidates=(
    "/usr/share/OVMF/OVMF_CODE.fd"
    "/usr/share/ovmf/OVMF.fd"
    "/usr/share/edk2/ovmf/OVMF_CODE.fd"
    "/usr/share/qemu/OVMF.fd"
  )
  for f in "${candidates[@]}"; do
    if [ -f "$f" ]; then
      echo "$f"
      return 0
    fi
  done
  echo ""
}

# ── Create disk ───────────────────────────────────────────────────────────────
cmd_create() {
  mkdir -p "$VM_DIR"
  if [ -f "$DISK_IMAGE" ]; then
    warn "Disk image already exists: $DISK_IMAGE"
    echo -e "  ${MUTED}Delete it first if you want a fresh install.${RESET}"
    return
  fi
  info "Creating ${DISK_SIZE} disk image..."
  qemu-img create -f qcow2 "$DISK_IMAGE" "$DISK_SIZE"
  ok "Disk created: $DISK_IMAGE"
}

# ── Boot with ISO (installer) ─────────────────────────────────────────────────
cmd_install() {
  check_deps

  if [ ! -f "$ISO_PATH" ]; then
    fail "NixOS ISO not found: $ISO_PATH"
    info "Download it with:"
    echo ""
    echo "    curl -L 'https://releases.nixos.org/nixos/24.11/nixos-24.11.719113.50ab793786d9/nixos-minimal-24.11.719113.50ab793786d9-x86_64-linux.iso' \\"
    echo "      -o $ISO_PATH"
    echo ""
    exit 1
  fi

  # Create disk if it doesn't exist
  [ ! -f "$DISK_IMAGE" ] && cmd_create

  local ovmf; ovmf=$(find_ovmf)
  local bios_args=()
  if [ -n "$ovmf" ]; then
    bios_args=(-bios "$ovmf")
    info "UEFI firmware: $ovmf"
  else
    warn "OVMF not found — using legacy BIOS (install: sudo apt install ovmf)"
  fi

  echo ""
  ok "Booting NixOS installer..."
  info "SSH port forwarded: localhost:${VM_PORT_SSH} → VM:22"
  info "Forge port forwarded: localhost:${VM_PORT_FORGE} → VM:${VM_PORT_FORGE}"
  info "To SSH in: ssh -p ${VM_PORT_SSH} -o StrictHostKeyChecking=no root@localhost"
  echo ""

  qemu-system-x86_64 \
    -name "CHAROS Test VM" \
    -machine type=q35,accel=kvm \
    -cpu host \
    -smp "$VM_CPUS" \
    -m "$VM_RAM" \
    "${bios_args[@]}" \
    -drive file="$DISK_IMAGE",format=qcow2,if=virtio \
    -cdrom "$ISO_PATH" \
    -boot order=dc \
    -netdev user,id=net0,hostfwd=tcp::${VM_PORT_SSH}-:22,hostfwd=tcp::${VM_PORT_FORGE}-:${VM_PORT_FORGE} \
    -device virtio-net-pci,netdev=net0 \
    -vga virtio \
    -display gtk \
    -serial mon:stdio \
    -no-reboot
}

# ── Boot existing disk ────────────────────────────────────────────────────────
cmd_boot() {
  check_deps

  if [ ! -f "$DISK_IMAGE" ]; then
    fail "No disk image found: $DISK_IMAGE"
    info "Run './test-vm.sh' first to install."
    exit 1
  fi

  local ovmf; ovmf=$(find_ovmf)
  local bios_args=()
  [ -n "$ovmf" ] && bios_args=(-bios "$ovmf")

  ok "Booting CHAROS test VM..."
  info "SSH: ssh -p ${VM_PORT_SSH} -o StrictHostKeyChecking=no root@localhost"
  info "Forge: http://localhost:${VM_PORT_FORGE}"
  echo ""

  qemu-system-x86_64 \
    -name "CHAROS Test VM" \
    -machine type=q35,accel=kvm \
    -cpu host \
    -smp "$VM_CPUS" \
    -m "$VM_RAM" \
    "${bios_args[@]}" \
    -drive file="$DISK_IMAGE",format=qcow2,if=virtio \
    -boot order=c \
    -netdev user,id=net0,hostfwd=tcp::${VM_PORT_SSH}-:22,hostfwd=tcp::${VM_PORT_FORGE}-:${VM_PORT_FORGE} \
    -device virtio-net-pci,netdev=net0 \
    -vga virtio \
    -display gtk \
    -serial mon:stdio
}

# ── Status ────────────────────────────────────────────────────────────────────
cmd_status() {
  header

  # ISO
  if [ -f "$ISO_PATH" ]; then
    local iso_size; iso_size=$(du -h "$ISO_PATH" | cut -f1)
    ok "ISO: $ISO_PATH (${iso_size})"
  else
    warn "ISO: not downloaded yet"
    info "Path: $ISO_PATH"
  fi

  # Disk
  if [ -f "$DISK_IMAGE" ]; then
    local disk_size; disk_size=$(du -h "$DISK_IMAGE" | cut -f1)
    local disk_info; disk_info=$(qemu-img info "$DISK_IMAGE" 2>/dev/null | grep 'virtual size' | head -1)
    ok "Disk: $DISK_IMAGE (${disk_size} on disk — ${disk_info})"
  else
    warn "Disk: not created yet"
  fi

  # QEMU
  if command -v qemu-system-x86_64 &>/dev/null; then
    local qver; qver=$(qemu-system-x86_64 --version | head -1)
    ok "QEMU: $qver"
  else
    fail "QEMU: not installed"
  fi

  # KVM
  if [ -e /dev/kvm ]; then
    ok "KVM: available (hardware acceleration enabled)"
  else
    warn "KVM: not available (VM will run slowly)"
  fi

  # OVMF
  local ovmf; ovmf=$(find_ovmf)
  if [ -n "$ovmf" ]; then
    ok "OVMF: $ovmf"
  else
    warn "OVMF: not found (legacy BIOS will be used)"
  fi

  echo ""
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
header
COMMAND="${1:-install}"

case "$COMMAND" in
  install|"")  cmd_install ;;
  boot)        cmd_boot ;;
  create)      cmd_create ;;
  status)      cmd_status ;;
  *)
    fail "Unknown command: $COMMAND"
    echo -e "  ${MUTED}Usage: test-vm.sh [install|boot|create|status]${RESET}"
    exit 1
    ;;
esac

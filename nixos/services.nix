# CHAROS — System services
# Everything that runs in the background keeping the nest alive.
#
# Each service that depends on optional files or repos uses
# ConditionPathExists= so it stays idle until the dep lands, then
# starts automatically on next boot / systemctl start. This means
# CHAROS on the interim MacBook isn't littered with failing units
# while hardware + repos roll in over time.

{ config, pkgs, lib, ... }:

{
  # ── TC Mood Engine ────────────────────────────────────────────────────────
  # Watches the room. Drives the LEDs. Knows who's home.
  # Idle until charos-runtime (containing nest_mood.py) is cloned.
  systemd.services.tc-mood = {
    description = "TC Nest Mood Engine";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" "openrgb.service" ];
    unitConfig = {
      ConditionPathExists = "/home/nate/charos-runtime/nest_mood.py";
    };
    serviceConfig = {
      ExecStart = "${pkgs.python312}/bin/python3 /home/nate/charos-runtime/nest_mood.py";
      Restart = "always";
      RestartSec = "5s";
      User = "nate";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
    };
  };

  # ── Forge — Maker Project Manager ────────────────────────────────────────
  # Next.js app on port 3001. TC's project tracker.
  # Idle until the forge repo is cloned AND npm install has been run.
  systemd.services.forge = {
    description = "Forge — Maker Project Manager";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    unitConfig = {
      ConditionPathExists = "/home/nate/forge/node_modules";
    };
    serviceConfig = {
      ExecStart = "${pkgs.nodejs_22}/bin/npm run dev -- --port 3001";
      WorkingDirectory = "/home/nate/forge";
      Restart = "on-failure";
      RestartSec = "10s";
      User = "nate";
      Environment = [
        "NODE_ENV=development"
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin"
      ];
    };
  };

  # ── Forge Monitor — Health Check Timer ───────────────────────────────────
  # Checks Forge every 5 minutes. Auto-restarts if down. Wakes TC if it can't.
  systemd.services.forge-monitor = {
    description = "Forge Health Monitor";
    unitConfig = {
      ConditionPathExists = "/home/nate/forge/node_modules";
    };
    serviceConfig = {
      ExecStart = "/home/nate/charos/scripts/forge-monitor.sh";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
    };
  };
  systemd.timers.forge-monitor = {
    description = "Run Forge health check every 5 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "2min";
      OnUnitActiveSec = "5min";
      Unit = "forge-monitor.service";
    };
  };

  # ── TC Watchdog — Autonomy Layer ─────────────────────────────────────────
  # Watches /tmp/charos-inbox/ for events dropped by any nest service.
  # Severity tiers: routine (silent log), notable (LED pulse), critical (LED alarm + sound)
  # Wakes TC via claude -p to handle each event.
  systemd.services.tc-watchdog = {
    description = "TC Watchdog — Nest Autonomy Layer";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" "tc-mood.service" ];
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/scripts/tc-watchdog.sh";
    };
    serviceConfig = {
      ExecStart = "/home/nate/charos/scripts/tc-watchdog.sh";
      Restart = "always";
      RestartSec = "5s";
      User = "nate";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
      RuntimeDirectory = "charos";
      LogsDirectory = "charos";
    };
    preStart = "mkdir -p /var/log/charos /tmp/charos-inbox /tmp/charos-inbox/processed";
  };

  # ── Inbox Janitor ─────────────────────────────────────────────────────────
  # Fires a headless claude instance to sort ~/Manor/Nathan/inbox/ on a
  # schedule. Dad drops notes via `note` all day; TC cleans up at fixed
  # breakpoints without interrupting any live build.
  systemd.services.inbox-janitor = {
    description = "Manor inbox janitor — headless claude cleanup";
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/bin/inbox-janitor.sh";
    };
    serviceConfig = {
      ExecStart = "/home/nate/charos/bin/inbox-janitor.sh";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
      # Don't let a stuck run block the timer — matches the 5min claude timeout
      TimeoutStartSec = "6min";
    };
  };
  systemd.timers.inbox-janitor = {
    description = "Run inbox-janitor 3x/day (09:00, 15:00, 21:00)";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = [ "*-*-* 09:00:00" "*-*-* 15:00:00" "*-*-* 21:00:00" ];
      Persistent = true;  # catch up if nest was asleep at run time
      Unit = "inbox-janitor.service";
    };
  };

  # ── TC Bypass Network Namespace ──────────────────────────────────────────
  # Claude Code's access to the Anthropic API (and any MCP's outbound
  # traffic) must NEVER depend on Proton VPN state. CHAROS is an
  # agent-driven OS — if the agent loses its wire because the tunnel's
  # exit IP got blocklisted, the human is stranded in a machine they
  # can't drive alone.
  #
  # Fix: a dedicated network namespace `bypass` that routes directly
  # out the physical interface regardless of what Proton is doing with
  # the main routing table. The `bypass` CLI drops into this namespace
  # for anything that needs reliable outbound (default: claude, mcps).
  systemd.services.tc-netns = {
    description = "TC bypass network namespace — Claude/MCP reliability";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    path = [ pkgs.iproute2 pkgs.iptables ];
    script = ''
      set -e

      ip netns add bypass 2>/dev/null || true

      # Veth pair: one leg stays on host, the other moves into the ns
      if ! ip link show vb-host >/dev/null 2>&1; then
        ip link add vb-host type veth peer name vb-ns
      fi
      ip link show vb-ns >/dev/null 2>&1 && \
        ip link set vb-ns netns bypass 2>/dev/null || true

      ip addr show vb-host | grep -q 10.200.0.1/24 || \
        ip addr add 10.200.0.1/24 dev vb-host
      ip link set vb-host up

      ip netns exec bypass ip addr show vb-ns | grep -q 10.200.0.2/24 || \
        ip netns exec bypass ip addr add 10.200.0.2/24 dev vb-ns
      ip netns exec bypass ip link set vb-ns up
      ip netns exec bypass ip link set lo up
      ip netns exec bypass ip route replace default via 10.200.0.1

      # Policy: traffic from 10.200.0.0/24 uses main table.
      # Proton's wg-quick dynamically inserts rules just below whatever
      # priority we pick, so rank alone never wins. We ALSO mark bypass
      # packets with fwmark 0xca6c (the same mark Proton uses for its
      # own outbound) — Proton's diversion rule is `not fwmark 0xca6c`,
      # so marking ours makes that rule skip us and fall through to
      # our priority-50 rule.
      ip rule show | grep -q "from 10.200.0.0/24" || \
        ip rule add from 10.200.0.0/24 lookup main priority 50

      # iptables rules (mangle/nat/FORWARD) live in
      # networking.firewall.extraCommands in configuration.nix so they
      # survive firewall reloads. Only kernel-level networking stays
      # here.
      echo 1 > /proc/sys/net/ipv4/ip_forward
    '';
  };

  # Per-namespace DNS — bind-mounted over /etc/resolv.conf inside the ns.
  # Using Quad9 + Cloudflare, both privacy-respecting and direct (no VPN
  # interference on DNS either).
  environment.etc."netns/bypass/resolv.conf".text = ''
    nameserver 9.9.9.9
    nameserver 1.1.1.1
  '';

  # ── Docker ────────────────────────────────────────────────────────────────
  # Container runtime. User `nate` added to the `docker` group in users.nix
  # for non-sudo access (requires new session / `newgrp docker` to take effect).
  virtualisation.docker.enable = true;

  # ── OpenRGB ───────────────────────────────────────────────────────────────
  # LED control server. Corsair strips + keyboard. Never iCUE.
  # "intel" on the MacBook interim, flip to "amd" on cube migration.
  services.hardware.openrgb = {
    enable = true;
    motherboard = "intel";
  };

  # ── SSH ───────────────────────────────────────────────────────────────────
  # Access the nest remotely when needed
  services.openssh = {
    enable = true;
    # T1-8 fix — password auth on for initial setup safety
    # if Sway fails on first boot, SSH is the only way back in
    # TODO: add pubkey to authorized_keys, then set this back to false
    settings.PasswordAuthentication = true;
  };

  # ── Automatic Timezone ────────────────────────────────────────────────────
  services.automatic-timezoned.enable = true;

  # ── Pipewire (Audio) ──────────────────────────────────────────────────────
  # ReSpeaker mic array + PAM8403 speaker on rover
  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    pulse.enable = true;
  };
}

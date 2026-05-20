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

  # ── tmux Reaper — Ghost Session Cleanup ────────────────────────────────────
  # Kills detached tmux sessions with no active child processes.
  # Runs at 7am — either sleep time or weed time, either way Dad won't
  # notice his ghost sessions being reaped.
  systemd.services.tmux-reaper = {
    description = "tmux Reaper — kill ghost sessions";
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/bin/tmux-reaper";
    };
    serviceConfig = {
      ExecStart = "/home/nate/charos/bin/tmux-reaper --kill";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
    };
  };
  systemd.timers.tmux-reaper = {
    description = "Reap ghost tmux sessions daily at 7am";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 07:00:00";
      Persistent = true;
      Unit = "tmux-reaper.service";
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

  # ── HAROS FOV — Battalion Field of View ────────────────────────────────────
  # Web-based tmux session viewer for orchestrating parallel HAROS builds.
  # Port 4200. Discovers haros-* sessions, serves xterm.js terminals in browser.
  # Accessible from any machine on Tailscale.
  systemd.services.haros-fov = {
    description = "HAROS FOV — Battalion Session Viewer";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/haros-fov/server.py";
    };
    serviceConfig = {
      ExecStart = "/run/current-system/sw/bin/python3 -m uvicorn server:app --host 0.0.0.0 --port 4200";
      WorkingDirectory = "/home/nate/charos/haros-fov";
      Restart = "on-failure";
      RestartSec = "10s";
      User = "nate";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
      ];
    };
  };

  # ── tc-timer Daemon — ADHD Timer Prosthetic ──────────────────────────────
  # Fires every 60s, scans ~/.claude/timers/ for pending timers.
  # Haiku composes the reminder, tc-say speaks it.
  systemd.services.tc-timer-daemon = {
    description = "tc-timer daemon — fire pending ADHD timers";
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/bin/tc-timer-daemon";
    };
    serviceConfig = {
      ExecStart = "${pkgs.python312}/bin/python3 /home/nate/charos/bin/tc-timer-daemon";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/current-system/sw/bin:/run/wrappers/bin:/home/nate/.local/bin"
        # Audio env so tc-say can reach Pipewire and actually play sound.
        # Without these, piper renders the .wav but nothing gets to the speakers.
        "XDG_RUNTIME_DIR=/run/user/1000"
        "PULSE_SERVER=unix:/run/user/1000/pulse/native"
      ];
      LogsDirectory = "charos";
    };
    preStart = "mkdir -p /home/nate/.claude/timers";
  };
  systemd.timers.tc-timer-daemon = {
    description = "Fire tc-timer-daemon every 60 seconds";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "1min";
      OnUnitActiveSec = "1min";
      Unit = "tc-timer-daemon.service";
    };
  };

  # ── scout-pulse-poll — Live family activity snapshot ────────────────────
  # Polls tmux state, transcript dir, and Claude Code session activity.
  # Writes to raw_session_pulse table in family-brain Postgres every 1 min.
  # Cross-machine: tc-nest's run polls itself + SSHes to jarvis-wsl.
  # Authored by TC, on behalf of Scout, 2026-04-24 (handoff doc in scout-pipeline).
  # Secrets in /etc/scout-pulse.env (mode 600, not in nix store, not git-tracked).
  systemd.services.scout-pulse-poll = {
    description = "Scout pulse poll — live family activity snapshot";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m collection.scout_pulse_poll";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      # /run/wrappers/bin MUST come first — that's where NixOS keeps the
      # setuid'd sudo. The non-wrapped sudo in /run/current-system/sw/bin
      # lacks the setuid bit and refuses to run.
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "30s";
    };
  };
  systemd.timers.scout-pulse-poll = {
    description = "Fire scout-pulse-poll every 1 minute";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "30s";
      OnUnitActiveSec = "1min";
      Unit = "scout-pulse-poll.service";
    };
  };

  # ── scout-baseline — 7-day rolling stats per signal ──────────────────────
  # Computes mean + std-dev across the last 7 days of daily_ledgers for each
  # signal Scout tracks. Feeds the Z-score logic in trajectories + summarize.
  systemd.services.scout-baseline = {
    description = "Scout baseline — 7-day rolling stats per signal";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_baseline";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "5min";
    };
  };
  systemd.timers.scout-baseline = {
    description = "Run scout-baseline nightly at 22:30";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 22:30:00";
      Persistent = true;
      Unit = "scout-baseline.service";
    };
  };

  # ── scout-trajectories — 4-way per-signal trajectory comparisons ─────────
  # Reads daily_ledgers + signal_baselines, writes signal_trajectories.
  # Scout reads these to decide which deviations to surface in summaries.
  systemd.services.scout-trajectories = {
    description = "Scout trajectories — 4-way per-signal comparisons";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_trajectories";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "5min";
    };
  };
  systemd.timers.scout-trajectories = {
    description = "Run scout-trajectories nightly at 22:45";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 22:45:00";
      Persistent = true;
      Unit = "scout-trajectories.service";
    };
  };

  # ── scout-summarize — Scout writes Yesterday's prose ─────────────────────
  # Reads trajectories + patterns + learning_notes, calls Anthropic API
  # (claude-haiku-4-5), writes scout_compositions row. Falls back to a
  # template-only render if ANTHROPIC_API_KEY is unset.
  systemd.services.scout-summarize = {
    description = "Scout summarize — write yesterday's prose to scout_compositions";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_summarize";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "5min";
    };
  };
  systemd.timers.scout-summarize = {
    description = "Run scout-summarize nightly at 23:05 (after baseline + trajectories)";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 23:05:00";
      Persistent = true;
      Unit = "scout-summarize.service";
    };
  };

  # ── scout-dad-status — 'How is Dad right now' composer ──────────────────
  # Same pipeline as scout-summarize, different prompt + composition_type.
  # Fires every 5 min so the dashboard's "Dad, right now" block stays fresh.
  # Uses Haiku, ~$0.001/render, ~$8/mo at the 5-min cadence.
  systemd.services.scout-dad-status = {
    description = "Scout dad-status — 'how is Dad right now' composer";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_summarize --dad-status";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "60s";
    };
  };
  systemd.timers.scout-dad-status = {
    description = "Render dad-status every 5 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "2min";
      OnUnitActiveSec = "5min";
      Unit = "scout-dad-status.service";
    };
  };

  # ── scout-decisions — Decision queue narration + priority scoring ───────
  # Composes per-decision body + Scout-contextual button labels via Haiku
  # for every pending decision. Fires every 5 min so newly-flagged decisions
  # get composed quickly and priority scores stay fresh.
  systemd.services.scout-decisions = {
    description = "Scout decisions — narrative + button generation per pending decision";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_summarize --decisions";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "120s";
    };
  };
  systemd.timers.scout-decisions = {
    description = "Recompose decision queue every 5 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "3min";
      OnUnitActiveSec = "5min";
      Unit = "scout-decisions.service";
    };
  };

  # ── scout-top-pick — Editorial top-of-day item ──────────────────────────
  # Scout picks ONE item to surface as Top from Scout. Refreshes every 15
  # min so it doesn't bounce around constantly mid-thought.
  systemd.services.scout-top-pick = {
    description = "Scout top-pick — editorial 'top from Scout today'";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_summarize --top-pick";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "60s";
    };
  };
  systemd.timers.scout-top-pick = {
    description = "Refresh Scout's top pick every 15 minutes";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "4min";
      OnUnitActiveSec = "15min";
      Unit = "scout-top-pick.service";
    };
  };

  # ── scout-reminders — time-anchored ntfy nudges ──────────────────────────
  # Currently checks pharmacy refill (30-day cycle). Fires a soft warning
  # at day 25, urgent at day 30, daily reminder once overdue. Idempotent
  # per-day per-reminder-type so we don't spam.
  systemd.services.scout-reminders = {
    description = "Scout reminders — pharmacy refill + future time-anchored nudges";
    unitConfig = {
      ConditionPathExists = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3";
    };
    serviceConfig = {
      ExecStart = "/home/nate/Manor/Scout/projects/scout-pipeline/.venv/bin/python3 -m aggregation.scout_reminders";
      WorkingDirectory = "/home/nate/Manor/Scout/projects/scout-pipeline";
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "60s";
    };
  };
  systemd.timers.scout-reminders = {
    description = "Run scout-reminders daily at 12:00 EDT";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 12:00:00";
      Persistent = true;
      Unit = "scout-reminders.service";
    };
  };

  # ── bus-latest-export — agent-to-agent notification via CLAUDE.md ───────
  # Polls the family bus every minute, writes the last 24h of messages to
  # ~/family-bus/latest-messages.md, which is @-referenced from
  # ~/.claude/CLAUDE.md so every cold-boot family agent arrives with
  # recent bus traffic in context. Solves the auto-notify backlog item.
  # Designed by Nathan ~07:00 EDT 2026-04-25 after Dario nerfed `sleep`.
  systemd.services.bus-latest-export = {
    description = "Bus latest-export — refresh ~/family-bus/latest-messages.md";
    unitConfig = {
      ConditionPathExists = "/home/nate/charos/bin/bus-latest-export";
    };
    serviceConfig = {
      ExecStart = "/run/current-system/sw/bin/python3 /home/nate/charos/bin/bus-latest-export";
      User = "nate";
      Type = "oneshot";
      Environment = [
        "HOME=/home/nate"
        "PATH=/run/wrappers/bin:/run/current-system/sw/bin:/home/nate/.local/bin"
      ];
      TimeoutStartSec = "30s";
    };
  };
  systemd.timers.bus-latest-export = {
    description = "Refresh bus latest-messages every minute";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnBootSec = "30s";
      OnUnitActiveSec = "1min";
      Unit = "bus-latest-export.service";
    };
  };

  # ── scout-pulse-shred — TTL cleanup for raw_session_pulse ────────────────
  # Deletes raw_session_pulse rows older than 14 days. Patterns extracted from
  # the data live forever in `patterns` table; raw pulse data shreds.
  systemd.services.scout-pulse-shred = {
    description = "Shred raw_session_pulse rows older than 14 days";
    unitConfig = {
      ConditionPathExists = "/etc/scout-pulse.env";
    };
    serviceConfig = {
      # systemd's `Environment=` doesn't perform $VAR expansion — the literal
      # string `$SCOUT_PG_PASSWORD` would be set instead of the loaded value.
      # Wrap the command in a shell so the env var (loaded via EnvironmentFile)
      # expands correctly into PGPASSWORD at exec time.
      ExecStart = pkgs.writeShellScript "scout-pulse-shred" ''
        set -euo pipefail
        PGPASSWORD="$SCOUT_PG_PASSWORD" ${pkgs.postgresql}/bin/psql \
          "host=jarvis-wsl port=5432 dbname=family_brain user=harrell" \
          -c "DELETE FROM raw_session_pulse WHERE event_time < NOW() - INTERVAL '14 days';"
      '';
      EnvironmentFile = "/etc/scout-pulse.env";
      User = "nate";
      Type = "oneshot";
    };
  };
  systemd.timers.scout-pulse-shred = {
    description = "Run scout-pulse-shred nightly at 03:00";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      OnCalendar = "*-*-* 03:00:00";
      Persistent = true;
      Unit = "scout-pulse-shred.service";
    };
  };

  # ── dnsmasq — harrell.ai Internal DNS ────────────────────────────────────
  # Resolves *.harrell.ai → 100.75.84.100 (Jarvis Tailscale IP).
  # Listens only on tc-nest's Tailscale interface (100.110.214.44) so it
  # doesn't interfere with system DNS on the main interface.
  # Tailscale admin: custom nameserver 100.110.214.44, restricted to harrell.ai
  services.dnsmasq = {
    enable = true;
    settings = {
      listen-address = "127.0.0.1,100.110.214.44";
      bind-dynamic = true;
      no-hosts = true;
      # Upstream resolvers for everything that isn't harrell.ai
      server = [ "1.1.1.1" "8.8.8.8" ];
      address = "/.harrell.ai/100.75.84.100";
    };
  };
  networking.firewall.allowedUDPPorts = [ 53 ];
  networking.firewall.allowedTCPPorts = [ 53 ];

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

  # ── Syncthing ─────────────────────────────────────────────────────────────
  # Bidirectional folder sync between tc-nest and jarvis-wsl. Currently
  # mirrors ~/Manor and ~/.claude (with .stignore exclusions for credentials
  # and machine-local settings). Devices + folders are managed at runtime
  # via GUI/REST so NixOS doesn't fight the dynamic config.
  #
  # GUI: http://127.0.0.1:8384 (loopback only — `ssh -L 8384:127.0.0.1:8384`
  # to reach it from elsewhere on the tailnet).
  # Bootstrapped 2026-05-20 to retire jarvis's stale Manor + .claude.
  services.syncthing = {
    enable = true;
    user = "nate";
    group = "users";
    dataDir = "/home/nate";
    configDir = "/home/nate/.config/syncthing";
    openDefaultPorts = true;
    guiAddress = "127.0.0.1:8384";
    overrideDevices = false;
    overrideFolders = false;
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

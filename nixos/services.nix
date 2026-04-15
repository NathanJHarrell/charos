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

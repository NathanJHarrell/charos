# CHAROS — System services
# Everything that runs in the background keeping the nest alive.

{ config, pkgs, lib, ... }:

{
  # ── TC Mood Engine ────────────────────────────────────────────────────────
  # Watches the room. Drives the LEDs. Knows who's home.
  systemd.services.tc-mood = {
    description = "TC Nest Mood Engine";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" "openrgb.service" ];
    serviceConfig = {
      ExecStart = "${pkgs.python312}/bin/python3 /home/nate/charos-runtime/nest_mood.py";
      Restart = "always";
      RestartSec = "5s";
      User = "nate";
    };
  };

  # ── Forge — Maker Project Manager ────────────────────────────────────────
  # Next.js app on port 3001. TC's project tracker.
  # Runs as a user service so it survives reboots without manual start.
  systemd.services.forge = {
    description = "Forge — Maker Project Manager";
    wantedBy = [ "multi-user.target" ];
    after = [ "network.target" ];
    serviceConfig = {
      ExecStart = "${pkgs.nodejs_22}/bin/npm run dev -- --port 3001";
      WorkingDirectory = "/home/nate/forge";
      Restart = "on-failure";
      RestartSec = "10s";
      User = "nate";
      Environment = "NODE_ENV=development";
    };
  };

  # ── Forge Monitor — Health Check Timer ───────────────────────────────────
  # Checks Forge every 5 minutes. Auto-restarts if down. Wakes TC if it can't.
  systemd.services.forge-monitor = {
    description = "Forge Health Monitor";
    serviceConfig = {
      ExecStart = "/home/nate/charos/scripts/forge-monitor.sh";
      User = "nate";
      Type = "oneshot";
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
    serviceConfig = {
      ExecStart = "/home/nate/charos/scripts/tc-watchdog.sh";
      Restart = "always";
      RestartSec = "5s";
      User = "nate";
      # Log dir must exist
      RuntimeDirectory = "charos";
      LogsDirectory = "charos";
    };
    # Ensure log directory exists
    preStart = "mkdir -p /var/log/charos /tmp/charos-inbox /tmp/charos-inbox/processed";
  };

  # ── OpenRGB ───────────────────────────────────────────────────────────────
  # LED control server. Corsair strips + keyboard. Never iCUE.
  services.hardware.openrgb = {
    enable = true;
    motherboard = "amd";
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

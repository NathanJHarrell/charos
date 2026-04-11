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
      ExecStart = "${pkgs.python312}/bin/python3 /home/nathan/charos-runtime/nest_mood.py";
      Restart = "always";
      RestartSec = "5s";
      User = "nathan";
    };
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
    settings.PasswordAuthentication = false;
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

# CHAROS — CHArizard OS
# NixOS system configuration
# Built by Nathan Harrell and TC. Frederick, MD. Spring 2026.
# This file IS the operating system. Change it, rebuild it, it's yours.

{ config, pkgs, lib, ... }:

{
  imports = [
    ./hardware-configuration.nix  # Generated on first install
    ./packages.nix                # Everything we install
    ./desktop.nix                 # Desktop environment
    ./services.nix                # TC mood engine, WLED, OpenRGB
    ./users.nix                   # Nathan's user config
  ];

  # ── Identity ─────────────────────────────────────────────────────────────
  networking.hostName = "tc-nest";
  time.timeZone = "America/New_York";
  i18n.defaultLocale = "en_US.UTF-8";

  # ── Boot ─────────────────────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # CHAROS boot splash — ember on charcoal
  boot.plymouth = {
    enable = true;
    theme = "charos";
  };

  # ── Hardware ──────────────────────────────────────────────────────────────
  hardware.opengl.enable = true;
  hardware.nvidia = {
    modesetting.enable = true;
    open = false;
    nvidiaSettings = true;
    package = config.boot.kernelPackages.nvidiaPackages.stable;
  };

  # USB devices — rover, sensors, cameras, WLED controllers
  services.udev.extraRules = ''
    # TOPDON TC001 thermal camera
    SUBSYSTEM=="usb", ATTRS{idVendor}=="2aaa", MODE="0666"
    # ReSpeaker mic array
    SUBSYSTEM=="usb", ATTRS{idProduct}=="0018", MODE="0666"
    # WS2812B / WLED ESP32
    SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666", GROUP="dialout"
  '';

  # ── Nix ───────────────────────────────────────────────────────────────────
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
  nixpkgs.config.allowUnfree = true;  # NVIDIA drivers need this

  system.stateVersion = "24.11";
}

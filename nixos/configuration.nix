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
  networking.networkmanager.enable = true;  # T1-7 fix — no network without this

  # Allow bypass netns (vb-host) to forward through to the world — this
  # has to live in the firewall config (not tc-netns's script) because
  # any firewall reload wipes rules added outside it. See services.nix
  # for the tc-netns netns setup.
  networking.firewall.extraCommands = ''
    iptables -I FORWARD -i vb-host -j ACCEPT
    iptables -I FORWARD -o vb-host -j ACCEPT
  '';
  services.tailscale.enable = true;  # Mesh VPN, joins Dad's existing tailnet

  # ── Proton VPN (WireGuard) ────────────────────────────────────────────────
  # Declarative tunnel — brings wg-quick-proton-us-nj.service up at boot.
  # Config file lives outside the repo (contains private keys); managed
  # with `sudo mv` once per server.
  networking.wg-quick.interfaces.proton-us-nj = {
    configFile = "/etc/wireguard/proton-us-nj.conf";
    # Not autostart — Proton blocks Anthropic API traffic from its exit
    # IPs, so auto-up on every rebuild strands Dad. Bring up manually
    # via `vpn on` when research/privacy matters.
    autostart = false;
  };
  # time.timeZone conflicts with automatic-timezoned in services.nix (T1-2 fix)
  # timezone is managed dynamically — set manually if automatic-timezoned ever gets removed
  i18n.defaultLocale = "en_US.UTF-8";

  # ── Boot ─────────────────────────────────────────────────────────────────
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # CHAROS boot splash — ember on charcoal
  # TODO: build charos theme, switch back from spinner when ready (T1-1)
  boot.plymouth = {
    enable = true;
    theme = "spinner";
  };

  # ── Hardware ──────────────────────────────────────────────────────────────
  hardware.graphics.enable = true;  # T1-6 fix — opengl renamed in NixOS 24.11
  hardware.facetimehd.enable = true;  # 2013 MBP FaceTime HD camera — out-of-tree Broadcom driver + firmware
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

  # ── nix-ld ────────────────────────────────────────────────────────────────
  # Run prebuilt Linux binaries (Claude Code, etc.) that expect glibc paths.
  # Without this, curl | bash installers fail on NixOS.
  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      stdenv.cc.cc.lib
      openssl
      zlib
      curl
      libxml2
    ];
  };

  system.stateVersion = "24.11";
}

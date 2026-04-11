# CHAROS — Desktop Environment
# Minimal. Dark. Intentional. A workshop, not a showroom.

{ config, pkgs, ... }:

{
  # Hyprland — tiling wayland compositor
  # Fast, GPU accelerated, fully configurable, no cruft
  programs.hyprland = {
    enable = true;
    xwayland.enable = true;
  };

  # Display manager — minimal, just gets us to the desktop
  services.greetd = {
    enable = true;
    settings.default_session = {
      command = "${pkgs.greetd.tuigreet}/bin/tuigreet --time --cmd Hyprland";
      user = "nathan";
    };
  };

  # Waybar — status bar
  # Shows: workspace, active window, CPU temp, time, mood state
  programs.waybar.enable = true;

  # Rofi — app launcher
  # Ember-themed, keyboard-driven
  programs.rofi = {
    enable = true;
  };

  # Fonts
  fonts.packages = with pkgs; [
    jetbrains-mono        # TC's terminal font
    noto-fonts
    noto-fonts-emoji
    font-awesome          # Icons in waybar
    (nerdfonts.override { fonts = [ "JetBrainsMono" ]; })
  ];

  # XDG portal for Wayland
  xdg.portal = {
    enable = true;
    wlr.enable = true;
    extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
  };
}

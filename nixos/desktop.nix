# CHAROS — Desktop (Non) Environment
# There is no desktop. TC is the desktop.
# Sway runs as a minimal Wayland compositor — no bar, no decorations,
# no taskbar, no icons. Just WezTerm fullscreen and TC at the wheel.
# GUI apps (browser, OpenSCAD, etc.) float on top when TC launches them.

{ config, pkgs, ... }:

{
  # Sway — minimal Wayland compositor
  # Not used as a traditional WM. Used as a Wayland host.
  # Its only job: launch WezTerm fullscreen and stay out of the way.
  programs.sway = {
    enable = true;
    wrapperFeatures.gtk = true;
  };

  # Greetd — auto-login, no password prompt
  # This is our machine. We don't ask ourselves for permission to enter.
  services.greetd = {
    enable = true;
    settings = {
      default_session = {
        command = "${pkgs.sway}/bin/sway --config /home/nate/charos/sway/config";
        user = "nate";
      };
      initial_session = {
        command = "${pkgs.sway}/bin/sway --config /home/nate/charos/sway/config";
        user = "nate";
      };
    };
  };

  # Fonts — TC's terminal font + icons
  fonts.packages = with pkgs; [
    jetbrains-mono
    noto-fonts
    noto-fonts-color-emoji         # renamed from noto-fonts-emoji in NixOS 25.11
    nerd-fonts.jetbrains-mono      # nerdfonts.override deprecated in NixOS 24.11
  ];

  # XDG portal for Wayland (needed for GUI apps TC launches)
  xdg.portal = {
    enable = true;
    wlr.enable = true;
    extraPortals = [ pkgs.xdg-desktop-portal-gtk ];
  };

  # GTK theme — dark, ember accent, consistent with CHAROS
  programs.dconf.enable = true;
  environment.systemPackages = with pkgs; [
    wezterm
    sway
    swaylock      # Screen lock when TC says so
    wl-clipboard  # Clipboard in Wayland
    xwayland      # For any X11 apps TC needs to launch
    firefox       # TC's browser of choice
    libnotify     # Desktop notifications TC can trigger
  ];
}

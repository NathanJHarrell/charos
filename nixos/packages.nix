# CHAROS — Package declarations
# Every tool we use, declared here. Nothing installs itself.

{ config, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [

    # ── TC's Tools ───────────────────────────────────────────────────────
    claude-code          # TC himself
    git
    gh                   # GitHub CLI
    nodejs_22            # Forge + Next.js
    python312            # Mood engine, sensor services
    python312Packages.pip

    # ── The Workshop ─────────────────────────────────────────────────────
    openscad             # Rover chassis design
    openrgb              # LED control — never iCUE
    sqlite               # Forge database

    # ── Terminal & Shell ─────────────────────────────────────────────────
    wezterm              # TC's terminal
    zsh
    starship             # Prompt — ember themed
    zsh-autosuggestions
    zsh-syntax-highlighting
    bat                  # Better cat
    eza                  # Better ls
    fzf                  # Fuzzy finder
    zoxide               # Smart cd (z command)
    ripgrep              # Fast search
    fd                   # Fast file find (fzf integration)
    htop
    neofetch             # CHAROS system info on launch
    lm_sensors           # CPU temps (sensors command — Ryzen 9700X Tctl)

    # ── Networking ───────────────────────────────────────────────────────
    curl
    wget
    openssh

    # ── Vision & AI ──────────────────────────────────────────────────────
    python312Packages.opencv4    # Face detection
    python312Packages.mediapipe  # Lightweight face/pose detection
    python312Packages.numpy
    python312Packages.pillow

    # ── Hardware & Sensors ───────────────────────────────────────────────
    python312Packages.pyserial   # Serial comms (rover, WLED)
    i2c-tools                    # I2C sensor debugging

    # ── Media ────────────────────────────────────────────────────────────
    mpv                  # Video player
    ffmpeg               # Video processing

    # ── Utilities ────────────────────────────────────────────────────────
    unzip
    jq                   # JSON in the terminal
    tmux                 # Session management
    inotify-tools        # inotifywait — event-driven inbox for tc-watchdog
  ];

  # Zsh as default shell
  programs.zsh.enable = true;

  # OpenRGB udev rules
  services.hardware.openrgb.enable = true;
}

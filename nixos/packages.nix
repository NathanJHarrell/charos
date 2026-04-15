# CHAROS — Package declarations
# Every tool we use, declared here. Nothing installs itself.

{ config, pkgs, ... }:

{
  environment.systemPackages = with pkgs; [

    # ── TC's Tools ───────────────────────────────────────────────────────
    # claude-code is NOT in nixpkgs — install via native installer post-boot: (T1-3 fix)
    #   curl -fsSL https://claude.ai/install.sh | bash
    # npm install is deprecated and insecure. Native installer auto-updates.
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
    vim                  # Dad's editor of choice. Classic, not neo.
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
    wireguard-tools      # Proton VPN (and any other WireGuard tunnel) via wg-quick
    tailscale            # Mesh VPN — reach tower's Vaultwarden, future NAS, etc.
    usbutils             # lsusb — hardware debugging
    pciutils             # lspci — hardware debugging
    v4l-utils            # v4l2-ctl — camera debugging

    # ── Vision & AI ──────────────────────────────────────────────────────
    # python312Packages.opencv   # Face detection — package name unstable across NixOS versions, skip for now
    # python312Packages.mediapipe — NOT in nixpkgs, needs custom overlay (T1-4 fix)
    # TODO: build mediapipe overlay when face detection work resumes
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

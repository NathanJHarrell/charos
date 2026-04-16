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

    # ── Agent CLIs ──────────────────────────────────────────────────────
    # The AI tooling cabinet. Claude Code is installed separately via its
    # own installer (not in nixpkgs). These are the complementary ones.
    aider-chat-full      # Multi-provider AI pair programmer
    codex                # OpenAI Codex CLI
    codex-acp            # Codex agent-control-protocol
    gemini-cli           # Google Gemini
    qwen-code            # Alibaba Qwen
    ollama               # Local LLM runner (CPU variant — alias for ollama-cpu)
    # Python bundled with every library CHAROS scripts need, reachable by
    # plain `python3` or `#!/usr/bin/env python3`. Adding a python312Packages.*
    # line to systemPackages alone does NOT add to sys.path — it has to be
    # a withPackages wrap for the modules to import from the shebang.
    (python312.withPackages (ps: with ps; [
      pip
      numpy
      pillow
      pyserial          # Serial comms (rover, WLED)
      opencv4           # Vision primitives
      dlib              # HOG/CNN face detectors + 128-d embeddings
      face-recognition  # High-level wrapper on dlib
      face-recognition-models
      sounddevice       # Mic capture for tc-listen / tc-phone
      faster-whisper    # High-accuracy offline STT
      speechbrain       # ECAPA-TDNN speaker embeddings — voice-print ID
      soundfile         # Read/write WAVs for the voice-enroll pipeline
    ]))

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
    glow                 # Terminal markdown reader
    htop
    neofetch             # CHAROS system info on launch
    lm_sensors           # CPU temps (sensors command — Ryzen 9700X Tctl)

    # ── Networking ───────────────────────────────────────────────────────
    curl
    wget
    openssh
    wireguard-tools      # Proton VPN (and any other WireGuard tunnel) via wg-quick
    tailscale            # Mesh VPN — reach tower's Vaultwarden, future NAS, etc.
    sshfs                # Mount jarvis:/home/nate over Tailscale SSH
    usbutils             # lsusb — hardware debugging
    pciutils             # lspci — hardware debugging
    v4l-utils            # v4l2-ctl — camera debugging

    # ── Vision & AI ──────────────────────────────────────────────────────
    # opencv4, dlib, face-recognition are bundled into the python3
    # above via withPackages. Keeping this section header for future
    # non-Python tools (models, datasets, etc.).
    # python312Packages.mediapipe — NOT in nixpkgs, needs custom overlay

    # ── Hardware & Sensors ───────────────────────────────────────────────
    i2c-tools                    # I2C sensor debugging

    # ── Media ────────────────────────────────────────────────────────────
    mpv                  # Video player
    ffmpeg               # Video processing
    imv                  # Wayland-native image viewer — imv /path/to.png
    piper-tts            # Local neural TTS for tc-say / tc-phone
    whisper-cpp          # Fast whisper for light STT tasks

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

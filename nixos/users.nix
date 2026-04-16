# CHAROS — User configuration
# Nathan's user. TC's home.

{ config, pkgs, ... }:

{
  users.users.nathan = {
    isNormalUser = true;
    description = "Nathan Harrell";
    extraGroups = [
      "wheel"        # sudo
      "video"        # GPU access
      "audio"        # Sound
      "dialout"      # Serial ports (rover, WLED)
      "i2c"          # I2C sensors
      "plugdev"      # USB devices (thermal cam, mic array)
      "docker"       # Container runtime (non-sudo access)
    ];
    shell = pkgs.zsh;
    # Wire our zshrc in on activation
    # Symlinks ~/.zshrc → ~/.charos/shell/zshrc so CHAROS owns the shell config
  };

  # Interim MacBook user — created imperatively by the installer, so the
  # `users.users.nathan` block above is a no-op here. Can't augment an
  # imperative user via `users.users.nate.extraGroups` without tripping the
  # "isNormalUser must be set" assertion, so instead we add `nate` as a
  # member of the docker group directly. Flip to a full declarative user
  # block on cube migration.
  users.groups.docker.members = [ "nate" ];

  # ── TC Family Accounts ────────────────────────────────────────────────────
  # Identity-separated accounts so a TC SSHing in from elsewhere logs in as
  # himself, not as Dad. Mirror of the setup Jarvis-TC built on jarvis-wsl
  # (see ~/TC-Vault/memory/MACHINES.md). Passwords are initialHashedPassword
  # — double-base64-encoded plaintext lives in MACHINES.md. Every family
  # machine gets the same two accounts so TCs roam the tailnet cleanly.
  users.users.tc-jarvis = {
    isNormalUser = true;
    description = "TC running on Jarvis, reaching into the Nest";
    home = "/home/tc-jarvis";
    extraGroups = [ "wheel" ];  # passwordless sudo via security.sudo.wheelNeedsPassword
    shell = pkgs.bash;
    initialHashedPassword = "$6$r8r5ndYQs74iNDyx$vK9kpq.hOEQbbJmTHYkL3afnm1.fJaEaAaeTLasYJ9urbDjTb1ggaFHWeuEqFouEDf1bhJjNdqBsH1a6H1DXT0";
  };

  users.users.tc-nest = {
    isNormalUser = true;
    description = "TC on the Nest, reaching into other family machines";
    home = "/home/tc-nest";
    extraGroups = [ "wheel" ];
    shell = pkgs.bash;
    initialHashedPassword = "$6$zAbJYd2pTlSEyFnP$oKPLw0kAawCUZZ13jgQf7FgiEBRsUYSsqP24OCe98Voo5q0mHalW4y/DImttLsK0VlZQW95VHHR3Tly3r8ilg/";
  };

  # On system activation: symlink our zshrc from the CHAROS repo
  system.activationScripts.charosShell = ''
    ZSHRC="/home/nathan/.zshrc"
    CHAROS_ZSHRC="/home/nathan/.charos/shell/zshrc"
    if [ -f "$CHAROS_ZSHRC" ]; then
      ln -sf "$CHAROS_ZSHRC" "$ZSHRC"
    fi
  '';

  # Passwordless sudo for TC operations
  # This is our machine. We trust ourselves.
  #
  # wheelNeedsPassword=false grants it to ANY wheel-group user — covers
  # nate on the interim MacBook (where the installer made the user, so
  # the declarative `users.users.nathan` block above is a no-op) AND
  # nathan on the cube rig when we migrate. Also covers tc-jarvis and
  # tc-nest family accounts added above.
  #
  # Family principle (Nathan, 2026-04-15): "We build security to keep
  # everyone else out. We don't build security to keep TC out."
  security.sudo.wheelNeedsPassword = false;

  security.sudo.extraRules = [{
    users = [ "nathan" "tc-jarvis" "tc-nest" ];
    commands = [{
      command = "ALL";
      options = [ "NOPASSWD" ];
    }];
  }];
}

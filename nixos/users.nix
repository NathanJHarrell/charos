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
    ];
    shell = pkgs.zsh;
    # Wire our zshrc in on activation
    # Symlinks ~/.zshrc → ~/.charos/shell/zshrc so CHAROS owns the shell config
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
  security.sudo.extraRules = [{
    users = [ "nathan" ];
    commands = [{
      command = "ALL";
      options = [ "NOPASSWD" ];
    }];
  }];
}

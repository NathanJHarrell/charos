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
  };

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

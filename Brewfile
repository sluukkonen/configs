# vim: ft=ruby

require "socket"

tap "homebrew/bundle"
tap "homebrew/cask-fonts"
tap "homebrew/services"
tap "koekeishiya/formulae"
tap "nikitabobko/tap"

brew "bat"
brew "colima"
brew "coreutils"
brew "docker"
brew "docker-buildx"
brew "docker-compose"
brew "docker-credential-helper"
brew "eza"
brew "fnm"
brew "fzf"
brew "gh"
brew "ghcup"
brew "git"
brew "git-absorb"
brew "git-delta"
brew "git-interactive-rebase-tool"
brew "gnupg"
brew "grep"
brew "htop"
brew "httpie"
brew "jq"
brew "mas"
brew "p7zip"
brew "pgcli"
brew "pinentry-mac"
brew "rg"
brew "rustup-init"
brew "shellcheck"
brew "sponge"
brew "tig"
brew "tmux"
brew "tree"
brew "vim"
brew "wget"
brew "ykman"
brew "zsh"

cask "1password"
cask "aerospace"
cask "alacritty"
cask "discord"
cask "firefox"
cask "font-cascadia-code-pl"
cask "keycastr"
cask "maccy"
cask "notunes"
cask "pocket-casts"
cask "slack"
cask "spotify"
cask "webstorm"
cask "whatsapp"

mas "Pixelmator", id: 407963104
mas "Xcode", id: 497799835

if Socket.gethostname.start_with? "R"
  brew "aws-vault"
  brew "awscli"
  brew "openconnect"
  cask "google-chrome"
  cask "viscosity"
  cask "zulip"
else
  cask "steam"
end

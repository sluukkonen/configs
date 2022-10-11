# vim: ft=ruby

require "socket"

tap "homebrew/bundle"
tap "homebrew/cask"
tap "homebrew/cask-fonts"
tap "homebrew/cask-versions"
tap "homebrew/core"
tap "homebrew/services"
tap "koekeishiya/formulae"

brew "bat"
brew "coreutils"
brew "exa"
brew "fzf"
brew "gh"
brew "ghcup"
brew "git"
brew "git-absorb"
brew "git-delta"
brew "gnupg"
brew "htop"
brew "httpie"
brew "git-interactive-rebase-tool"
brew "jq"
brew "mas"
brew "p7zip"
brew "rg"
brew "shellcheck"
brew "skhd"
brew "sponge"
brew "tig"
brew "tmux"
brew "tree"
brew "vim"
brew "wget"
brew "yabai"
brew "zsh"

cask "1password"
cask "alacritty"
cask "docker"
cask "discord"
cask "firefox"
cask "font-cascadia-code-pl"
cask "keycastr"
cask "maccy"
cask "notunes"
cask "pocket-casts"
cask "spotify"
cask "slack"
cask "visual-studio-code"
cask "webstorm"

mas "Pixelmator", id: 407963104
mas "Xcode", id: 497799835

if Socket.gethostname.start_with? "R"
  brew "awscli"
  cask "datagrip"
  cask "google-chrome"
  cask "viscosity"
end

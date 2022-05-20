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

cask "alacritty"
cask "clipy"
cask "docker"
cask "discord"
cask "firefox"
cask "font-cascadia-code-pl"
cask "keycastr"
cask "notunes"
cask "pocket-casts"
cask "spotify"
cask "visual-studio-code"
cask "webstorm"

mas "1Password", id: 1333542190
mas "Highlight", id: 572867415
mas "Kaleidoscope", id: 587512244
mas "Pixelmator", id: 407963104
mas "Slack", id: 803453959
mas "WhatsApp", id: 1147396723
mas "Xcode", id: 497799835

if Socket.gethostname.start_with? "L"
  brew "awscli"
  brew "terraform"
  brew "tflint"

  cask "aws-vault"
  cask "datagrip"
  cask "intellij-idea"
  cask "google-chrome-canary"
  cask "viscosity"
end

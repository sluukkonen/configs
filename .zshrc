export DOCKER_BUILDKIT=1
export EDITOR=vim
export GPG_TTY=$(tty)
export NVM_LAZY_LOAD=true
export PATH=~/.ghcup/bin:$PATH

NVM_LAZY_LOAD=true
ZSH_THEME="agnoster"
DISABLE_AUTO_UPDATE=true
ZSH="$(antibody home)/https-COLON--SLASH--SLASH-github.com-SLASH-robbyrussell-SLASH-oh-my-zsh"
source <(antibody init)
antibody bundle < ~/.zsh_plugins.txt
command -v exa >/dev/null && alias ls=exa

[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

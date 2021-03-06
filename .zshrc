ZSH_THEME="agnoster"
DISABLE_AUTO_UPDATE=true
ZSH="$(antibody home)/https-COLON--SLASH--SLASH-github.com-SLASH-robbyrussell-SLASH-oh-my-zsh"
source <(antibody init)
antibody bundle < ~/.zsh_plugins.txt
command -v exa >/dev/null && alias ls=exa

export DOCKER_BUILDKIT=1
export GPG_TTY=$(tty)
export PATH=~/.ghcup/bin:$PATH

[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

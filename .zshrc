# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

export DOCKER_BUILDKIT=1
export EDITOR=vim
export GPG_TTY=$TTY
export NVM_LAZY_LOAD=true
export PATH=~/.ghcup/bin:$PATH

DISABLE_AUTO_UPDATE=true
NVM_LAZY_LOAD=true
source <(antibody init)
antibody bundle < ~/.zsh_plugins.txt

command -v exa >/dev/null && alias ls=exa
command -v bat >/dev/null && alias cat=bat

[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

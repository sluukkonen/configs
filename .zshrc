# Enable Powerlevel10k instant prompt. Should stay close to the top of ~/.zshrc.
# Initialization code that may require console input (password prompts, [y/n]
# confirmations, etc.) must go above this block; everything else may go below.
if [[ -r "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh" ]]; then
  source "${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-${(%):-%n}.zsh"
fi

# Environment variables
export BAT_THEME="gruvbox-light"
export DOCKER_BUILDKIT=1
export EDITOR=vim
export GPG_TTY=$TTY
export PATH=~/.ghcup/bin:$PATH

# Shell settings
NVM_LAZY_LOAD=true
NVM_LAZY_LOAD_EXTRA_COMMANDS=yarn
ZSHZ_TRAILING_SLASH=1
ZSHZ_UNCOMMON=1

# Initialize zgen
source ~/.zgen/zgen.zsh

if ! zgen saved; then
    zgen oh-my-zsh

	zgen load agkozak/zsh-z
	zgen load lukechilds/zsh-nvm
	zgen load romkatv/powerlevel10k powerlevel10k
	zgen load zsh-users/zsh-autosuggestions
	zgen load zsh-users/zsh-completions

	zgen save
fi

# Machine-specific customizations.
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# Aliases
command -v exa >/dev/null && alias ls=exa
command -v batcat >/dev/null && alias bat=batcat
command -v vim >/dev/null && alias vi=vim

# To customize prompt, run `p10k configure` or edit ~/.p10k.zsh.
[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh

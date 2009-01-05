# General options
autoload -U compinit promptinit
compinit
promptinit
HISTSIZE=100
SAVEHIST=100
HISTFILE=~/.zshhistory
setopt append_history
setopt inc_append_history
setopt extended_history
setopt hist_find_no_dups
setopt hist_ignore_all_dups
setopt hist_reduce_blanks
setopt hist_ignore_space
setopt hist_no_store
setopt hist_no_functions
setopt no_hist_beep
setopt hist_save_no_dups


# Prompt Theme
export PROMPT="%n@%m %c %# "

# Aliases
alias loki='ssh saku@loki.endoftheinternet.org'
alias ls='ls --color=auto -F'
alias v='vim'
alias sv='sudo vim'

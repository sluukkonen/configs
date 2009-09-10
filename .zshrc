# General options
autoload -U compinit promptinit
compinit -C
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'
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
# Emacs style bindings
bindkey -e


# Prompt Theme
autoload -U colors zsh/terminfo # Used in the colour alias below
colors
setopt prompt_subst
PROMPT="%n%{$fg[blue]%}@%{$reset_color%}%m:%~ %% "

# Aliases
alias loki='ssh saku@loki.endoftheinternet.org'
alias melkki='ssh soluukko@melkki.cs.helsinki.fi'
alias irs='ssh soluukko@melkki.cs.helsinki.fi -t screen -dr'
alias ls='ls --color=auto -F'
alias la='ls -la'
alias v='vim'
alias sv='sudo vim'
alias e='emacsclient -t'
alias l='less'

# Shell settings
export EDITOR='emacsclient'
# Functions

extract () {
    local old_dirs current_dirs lower
    lower=${(L)1}
    old_dirs=( *(N/) )
    if [[ $lower == *.tar.gz || $lower == *.tgz ]]; then
        tar xvzf $1
    elif [[ $lower == *.gz ]]; then
        gunzip $1
    elif [[ $lower == *.tar.bz2 || $lower == *.tbz ]]; then
        tar xvjf $1
    elif [[ $lower == *.bz2 ]]; then
        bunzip2 $1
    elif [[ $lower == *.zip ]]; then
        unzip $1
    elif [[ $lower == *.rar ]]; then
        unrar e $1
    elif [[ $lower == *.tar ]]; then
        tar xvf $1
    elif [[ $lower == *.lha ]]; then
        lha e $1
    else
        print "Unknown archive type: $1"
        return 1
    fi
    # Change in to the newly created directory, and
    # list the directory contents, if there is one.
    current_dirs=( *(N/) )
    for i in {1..${#current_dirs}}; do
        if [[ $current_dirs[$i] != $old_dirs[$i] ]]; then
            cd $current_dirs[$i]
            break
        fi
    done
}

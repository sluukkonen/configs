# Colors
autoload -U colors && colors

# Allow substitutions in prompt
setopt PROMPT_SUBST

# Git integration
autoload -Uz vcs_info && vcs_info
zstyle ':vcs_info:*' enable git
zstyle ':vcs_info:*' check-for-changes true
zstyle ':vcs_info:*' stagedstr '%F{green}●%f'
zstyle ':vcs_info:*' unstagedstr '%F{yellow}●%f'
# zstyle ':vcs_info:*' formats ' [%F{magenta}%b%c%u]'

precmd () {
    if [[ -z $(git ls-files --other --exclude-standard 2> /dev/null) ]] {
        zstyle ':vcs_info:*' formats ' [%F{green}%b%f%c%u]'
    } else {
        zstyle ':vcs_info:*' formats ' [%F{green}%b%f%c%u%F{red}●%f]'
    }
 
    vcs_info
}

# Git status in $PROMPT
PROMPT='%n%{$fg[blue]%}@%{$reset_color%}%m:%{$fg[blue]%}%~%{$reset_color%}${vcs_info_msg_0_} '

# History
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=~/.history


## Completions
autoload -U compinit
compinit -C

## Case-insensitive word, partial word and substring completion
zstyle ':completion:*' matcher-list 'm:{a-zA-Z}={A-Za-z}' 'r:|[._-]=* r:|=*' 'l:|=* r:|=*'

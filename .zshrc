# Environment variables
export BAT_THEME=auto
export BAT_THEME_LIGHT="Catppuccin Latte"
export BAT_THEME_DARK="Catppuccin Frappe"
export EDITOR=vim
export GPG_TTY=$TTY

# Shell settings
DISABLE_AUTO_UPDATE=true
ZSHZ_TRAILING_SLASH=1
ZSHZ_UNCOMMON=1
plugins=(
  fzf
)

# Initialize zgenom
source ~/.zgenom/zgenom.zsh

if ! zgenom saved; then
    zgenom ohmyzsh

    zgenom load agkozak/zsh-z
    zgenom load zsh-users/zsh-autosuggestions
    zgenom load zsh-users/zsh-completions

    zgenom save
fi

# FNM
command -v fnm >/dev/null && eval "$(fnm env)"

# Machine-specific customizations.
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local

# Aliases
if command -v codex >/dev/null; then
  codex() {
    command codex --config 'notify=["ntfy-codex"]' "$@"
  }
fi

if command -v glow >/dev/null; then
  # glow's auto style can pick dark on a light terminal, so follow the system
  # appearance like Ghostty does. Dux (DMS) writes "default" in light mode.
  glow() {
    local style=auto
    if [[ $OSTYPE == darwin* ]]; then
      style=light
      [[ $(defaults read -g AppleInterfaceStyle 2>/dev/null) == Dark ]] && style=dark
    elif command -v gsettings >/dev/null; then
      style=light
      [[ $(gsettings get org.gnome.desktop.interface color-scheme 2>/dev/null) == "'prefer-dark'" ]] && style=dark
    fi
    # Page like bat does: less -F prints short output directly. glow refuses
    # to combine its pager with the TUI (-t), so leave paging off for that.
    local pager=true
    (( ${@[(I)-t|--tui]} )) && pager=false
    GLOW_PAGER=$pager PAGER='less -RF' command glow --style "$style" "$@"
  }
fi

command -v eza >/dev/null && alias ls=eza
command -v batcat >/dev/null && alias bat=batcat
command -v vim >/dev/null && alias vi=vim

# Let ctrl-enter run a command in Ghostty
bindkey '^[[27;5;13~' accept-line

# Prompt. Uses Starship defaults unless ~/.config/starship.toml exists.
command -v starship >/dev/null && eval "$(starship init zsh)"

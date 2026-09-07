typeset -U path PATH

# Use Homebrew's environment setup when it is installed. Check the inherited
# PATH first, then the standard Apple Silicon, Intel macOS, and Linux locations.
if (( $+commands[brew] )); then
  eval "$(brew shellenv)"
else
  for brew_path in \
    /opt/homebrew/bin/brew \
    /usr/local/bin/brew \
    /home/linuxbrew/.linuxbrew/bin/brew
  do
    if [[ -x "$brew_path" ]]; then
      eval "$("$brew_path" shellenv)"
      break
    fi
  done
fi

# Prefer user-installed programs and toolchains, but only when their bin
# directories exist. The unique path array prevents duplicate PATH entries.
typeset -a optional_bin_paths
optional_bin_paths=()
for bin_path in \
  "$HOME/.local/bin" \
  "$HOME/bin" \
  "$HOME/.cargo/bin" \
  "$HOME/.cabal/bin" \
  "$HOME/.ghcup/bin"
do
  [[ -d "$bin_path" ]] && optional_bin_paths+=("$bin_path")
done
path=("${optional_bin_paths[@]}" "${path[@]}")

unset optional_bin_paths bin_path brew_path

export LC_ALL=en_US.UTF-8  
export LANG=en_US.UTF-8
export NVM_LAZY_LOAD=true

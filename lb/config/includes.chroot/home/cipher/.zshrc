# CipherOS XLVII — ZSH config
HISTFILE=~/.zsh_history
HISTSIZE=50000; SAVEHIST=50000
setopt SHARE_HISTORY HIST_IGNORE_DUPS EXTENDED_HISTORY AUTO_CD NO_BEEP

[[ -f /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && \
    source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
[[ -f /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && \
    source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh

ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE="fg=#4a5568"
autoload -Uz compinit && compinit
zstyle ':completion:*' menu select
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Z}'

export EDITOR=nvim; export VISUAL=nvim; export PAGER=bat
export FZF_DEFAULT_OPTS='--height 40% --border --layout=reverse --color=border:#00d4ff,pointer:#00d4ff'
export OLLAMA_HOST="127.0.0.1:11434"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
export MOZ_ENABLE_WAYLAND=1
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

# Aliases
alias ls='eza --icons --group-directories-first'
alias ll='eza -la --icons --group-directories-first --git'
alias lt='eza --tree --icons --level=2'
alias cat='bat --style=plain'
alias grep='rg'
alias find='fd'
alias top='btop'
alias vim='nvim'; alias v='nvim'
alias g='git'; alias gs='git status'; alias gl='git log --oneline --graph -15'
alias clip='wl-copy'; alias paste='wl-paste'
alias screenshot='grim -g "$(slurp)" ~/Pictures/screenshot-$(date +%s).png'
alias ai='cipher chat'
alias ask='cipher quick-ask'
alias speak='cipher speak'
alias memory='cipher memory show'
alias briefing='cipher briefing'
alias cstatus='cipher status'
alias hypr-reload='hyprctl reload'

bindkey -e
bindkey '^R' history-incremental-search-backward
bindkey '^[[A' history-search-backward
bindkey '^[[B' history-search-forward

export STARSHIP_CONFIG=~/.config/starship.toml
command -v starship &>/dev/null && eval "$(starship init zsh)"
command -v fzf &>/dev/null && source /usr/share/doc/fzf/examples/key-bindings.zsh 2>/dev/null || true

[[ -z "$CIPHER_GREETED" ]] && {
    export CIPHER_GREETED=1
    echo -e "\033[0;36m⬡ CipherOS XLVII · Phantom Signal\033[0m  \033[2mType 'ai' to chat, 'cstatus' for status\033[0m"
}

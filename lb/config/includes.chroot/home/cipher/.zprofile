# CipherOS — login shell env
export XDG_CURRENT_DESKTOP=Hyprland
export XDG_SESSION_TYPE=wayland
export XDG_SESSION_DESKTOP=Hyprland
export QT_QPA_PLATFORM=wayland
export GDK_BACKEND=wayland
export SDL_VIDEODRIVER=wayland
export ELECTRON_OZONE_PLATFORM_HINT=auto

# Start Hyprland on tty1 if not already running
[[ -z "$WAYLAND_DISPLAY" && "$(tty)" == "/dev/tty1" ]] && exec Hyprland

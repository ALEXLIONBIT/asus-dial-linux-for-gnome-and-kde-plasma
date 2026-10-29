#!/usr/bin/env bash
# Installs ASUS Dial for GNOME and KDE Plasma for your user (apps, launchers, icons, service). Permissions need sudo once.
# AI models, Ollama, AirLLM, voice: the AI app installs those by itself the first time you use them.
set -eu
cd "$(dirname "$(readlink -f "$0")")"
BIN="$HOME/.local/bin"; APPS="$HOME/.local/share/applications"; ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$BIN" "$APPS" "$ICONS" "$HOME/.config/autostart" "$HOME/.config/systemd/user"
cp asus-dial asus-dial-ai asus-dial-ai-app asus-dial-gpu asus-dial-manager asus-dial-welcome asus_dial_*.py "$BIN/"
chmod +x "$BIN"/asus-dial "$BIN"/asus-dial-ai "$BIN"/asus-dial-ai-app "$BIN"/asus-dial-gpu "$BIN"/asus-dial-manager "$BIN"/asus-dial-welcome
ln -sf "$BIN/asus-dial-manager" "$BIN/dial"
cp icons/*.svg "$ICONS/"; gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
sed "s#^Exec=.*#Exec=$BIN/asus-dial-manager#" asus-dial-manager.desktop > "$APPS/asus-dial-manager.desktop"
sed "s#^Exec=.*#Exec=$BIN/asus-dial-ai-app#" asus-dial-ai.desktop > "$APPS/asus-dial-ai.desktop"
sed "s#^Exec=.*#Exec=$BIN/asus-dial-welcome#" asus-dial-welcome.desktop > "$HOME/.config/autostart/asus-dial-welcome.desktop"
update-desktop-database "$APPS" 2>/dev/null || true
cp systemd/asus-dial.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable asus-dial
systemctl --user restart asus-dial || true
if [ ! -e /etc/udev/rules.d/99-asus-dial.rules ]; then
  echo "Permissions (sudo, once):"
  sudo cp udev/99-asus-dial.rules /etc/udev/rules.d/
  echo uinput | sudo tee /etc/modules-load.d/uinput.conf >/dev/null
  sudo modprobe uinput
  sudo usermod -aG input "$USER"
  sudo udevadm control --reload-rules
  sudo udevadm trigger --subsystem-match=hidraw
  echo "Done. Log out and back in once so the 'input' group takes effect."
fi
echo "Installed. Open 'ASUS Dial AI' or 'ASUS Dial Manager' from the applications menu."

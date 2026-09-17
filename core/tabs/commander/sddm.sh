#!/bin/sh -e
# shellcheck source=core/tabs/commander/common.sh
. ./common.sh
commander_init
checkCommandRequirements 'sddm sddm-greeter-qt6 python3'
if [ -z "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    printf '%s\n' 'Run this installer from a graphical desktop session for the theme preview.' >&2
    exit 1
fi
python3 - "$(sddm --version)" <<'PY'
import re, sys
version = re.search(r'(\d+)\.(\d+)\.(\d+)', sys.argv[1])
if not version or tuple(map(int, version.groups())) < (0, 21, 0):
    sys.exit('SilentSDDM requires SDDM 0.21.0 or newer.')
PY
confirm 'Install your SilentSDDM Revan theme and Qt6 dependencies. SDDM must already be your display manager. Existing theme/config are backed up; the current session is not restarted.'
command_exists git || install_packages git
fetch_source dotfiles
case "$PACKAGER" in
    pacman) install_packages qt6-svg qt6-virtualkeyboard qt6-multimedia qt6-declarative qt6-imageformats ;;
    dnf) install_packages qt6-qtsvg qt6-qtvirtualkeyboard qt6-qtmultimedia qt6-qtdeclarative qt6-qtimageformats ;;
    apt-get | nala) install_packages libqt6svg6 qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts qml6-module-qtquick-window qml6-module-qtquick-templates qml6-module-qtqml-workerscript qml6-module-qtquick-effects qml6-module-qtquick-virtualkeyboard qml6-module-qtmultimedia qt6-image-formats-plugins ;;
esac
theme=/usr/share/sddm/themes/commander-silent
config=/etc/sddm.conf.d/zz-commander-theme.conf
backup_system "$theme"
backup_system "$config"
"$ESCALATION_TOOL" mkdir -p "$theme" /etc/sddm.conf.d
"$ESCALATION_TOOL" cp -a "$source_dir/sddm/." "$theme/"
backup_system /usr/local/share/fonts/commander-silent
"$ESCALATION_TOOL" mkdir -p /usr/local/share/fonts/commander-silent
"$ESCALATION_TOOL" cp -a "$source_dir/sddm/fonts/." /usr/local/share/fonts/commander-silent/
if command_exists fc-cache; then "$ESCALATION_TOOL" fc-cache -f /usr/local/share/fonts/commander-silent; fi
printf '%s\n' 'Preview the theme before enabling it. Close the preview window to continue.'
checkCommandRequirements 'sddm-greeter-qt6'
QML2_IMPORT_PATH="$theme/components" QT_IM_MODULE=qtvirtualkeyboard QML_XHR_ALLOW_FILE_READ=1 sddm-greeter-qt6 --test-mode --theme "$theme"
confirm 'If the preview rendered correctly, enable this theme for the next login.'
rendered=$(mktemp)
trap 'rm -f "$rendered"' 0
printf '%s\n' '[Theme]' 'Current=commander-silent' '[General]' 'InputMethod=qtvirtualkeyboard' "GreeterEnvironment=QML2_IMPORT_PATH=$theme/components/,QT_IM_MODULE=qtvirtualkeyboard,QML_XHR_ALLOW_FILE_READ=1" > "$rendered"
"$ESCALATION_TOOL" install -m 644 "$rendered" "$config"
if [ -f /etc/sddm.conf ]; then
    backup_system /etc/sddm.conf
    python3 ./configure.py sddm /etc/sddm.conf > "$rendered"
    "$ESCALATION_TOOL" install -m 644 "$rendered" /etc/sddm.conf
fi
printf '%s\n' 'Theme enabled for the next login. No service was restarted.'

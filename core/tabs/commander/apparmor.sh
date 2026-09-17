#!/bin/sh -e
# shellcheck source=core/tabs/commander/common.sh
. ./common.sh
commander_init
. ../common-service-script.sh
if [ "$DTYPE" = fedora ]; then
    printf '%s\n' 'Use the Fedora SELinux entry on this system.' >&2
    exit 1
fi
case "$PACKAGER" in
    pacman | apt-get | nala) ;;
    *) printf '%s\n' 'AppArmor setup currently supports Arch and Debian/Ubuntu families.'; exit 1 ;;
esac
if [ ! -r /sys/module/apparmor/parameters/enabled ] || ! grep -q '^Y' /sys/module/apparmor/parameters/enabled; then
    printf '%s\n' 'AppArmor is not enabled in the running kernel. Enable it using your distro boot configuration and reboot, then rerun this entry. No boot settings were changed.'
    exit 1
fi
confirm 'Install AppArmor tools and distro-provided profiles, then enable and start the AppArmor service. Existing enabled profiles may begin enforcing restrictions.'
case "$PACKAGER" in
    pacman) install_packages apparmor ;;
    *) install_packages apparmor apparmor-utils apparmor-profiles ;;
esac
startAndEnableService apparmor
"$ESCALATION_TOOL" aa-status

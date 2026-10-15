#!/bin/sh -e
# shellcheck source=core/tabs/commander/common.sh
. ./common.sh
# shellcheck source=core/tabs/commander/kernel-cmdline.sh
. ./kernel-cmdline.sh
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
    printf '%s\n' 'AppArmor is not enabled in the running kernel.'
    # Arch kernels build AppArmor in but start it only when the lsm= parameter
    # names it, the same parameter the dotfiles GRUB settings carry.
    if [ "$PACKAGER" = pacman ] && [ -f /etc/default/grub ]; then
        checkCommandRequirements 'python3'
        lsm='lsm=landlock,lockdown,yama,integrity,apparmor,bpf'
        grub_cmdline_setup 'AppArmor needs the lsm= kernel parameter; add it in your boot loader yourself, reboot, then rerun this entry.'
        confirm "Add $lsm to the kernel command line in /etc/default/grub (replacing any lsm= setting) and regenerate the GRUB menu, so the kernel starts AppArmor at the next boot. Defaults and the boot menu are backed up first. Reboot, then run this entry again to install the tools and enable the service."
        trap grub_cmdline_cleanup 0
        trap 'exit 130' INT
        trap 'exit 143' TERM
        grub_cmdline_apply set "$lsm"
        printf '%s\n' 'Reboot, then run this entry again to install the AppArmor tools and enable the service.'
        exit 0
    fi
    printf '%s\n' 'Enable it using your distro boot configuration and reboot, then rerun this entry. No boot settings were changed.'
    exit 1
fi
confirm 'Install AppArmor tools and distro-provided profiles, then enable and start the AppArmor service. Existing enabled profiles may begin enforcing restrictions.'
case "$PACKAGER" in
    pacman) install_packages apparmor ;;
    *) install_packages apparmor apparmor-utils apparmor-profiles ;;
esac
startAndEnableService apparmor
"$ESCALATION_TOOL" aa-status

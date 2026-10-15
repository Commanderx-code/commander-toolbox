#!/bin/sh -e
# shellcheck source=core/tabs/commander/common.sh
. ./common.sh
commander_init
checkCommandRequirements 'python3'
action=${1:-theme}
case "$action" in
    theme | on | off) ;;
    *) printf '%s\n' 'Unknown boot splash action.' >&2; exit 1 ;;
esac

# The splash is read from the initramfs, which each distro rebuilds differently.
initramfs_tool() {
    if command_exists dracut-rebuild; then
        printf 'dracut-rebuild'
    elif command_exists mkinitcpio; then
        printf 'mkinitcpio -P'
    elif command_exists update-initramfs; then
        printf 'update-initramfs -u -k all'
    elif command_exists dracut; then
        printf 'dracut --force --regenerate-all'
    fi
}
tool=$(initramfs_tool)
if [ -z "$tool" ]; then
    printf '%s\n' 'No initramfs tool (dracut, mkinitcpio or update-initramfs) was found; no changes made.' >&2
    exit 1
fi
rebuild_initramfs() {
    # The tool and its arguments are a fixed string chosen above.
    # shellcheck disable=SC2086
    "$ESCALATION_TOOL" $tool
}

if [ "$action" = theme ]; then
    checkCommandRequirements 'plymouth-set-default-theme'
    current=$(plymouth-set-default-theme)
    themes=$(plymouth-set-default-theme --list)
    if [ -z "$themes" ]; then
        printf '%s\n' 'No Plymouth themes are installed.' >&2
        exit 1
    fi
    printf 'Current boot splash: %s\nInstalled themes:\n' "$current"
    printf '%s\n' "$themes" | nl -w2 -s') '
    printf 'Theme number: '
    read -r answer
    case "$answer" in
        '' | *[!0-9]*) printf '%s\n' 'Cancelled.'; exit 1 ;;
    esac
    chosen=$(printf '%s\n' "$themes" | sed -n "${answer}p")
    [ -n "$chosen" ] || { printf '%s\n' 'Cancelled.'; exit 1; }
    confirm "Select the '$chosen' boot splash and rebuild the boot images with '$tool'. Kernel arguments and packages are not changed."
    "$ESCALATION_TOOL" plymouth-set-default-theme "$chosen"
    rebuild_initramfs
    printf 'Boot splash %s shows from the next reboot.\n' "$chosen"
    exit 0
fi

# Turning the splash on or off means editing the kernel command line, which
# this installer only does through /etc/default/grub.
if [ ! -f /etc/default/grub ]; then
    printf '%s\n' 'Boot splash changes need GRUB with /etc/default/grub. With systemd-boot or Limine, add or remove "splash" on the kernel command line yourself; no changes made.' >&2
    exit 1
fi
if [ "$DTYPE" = fedora ]; then
    generator=grub2-mkconfig
    checker=grub2-script-check
    output=/boot/grub2/grub.cfg
elif command_exists grub-mkconfig && [ -d /boot/grub ]; then
    generator=grub-mkconfig
    checker=grub-script-check
    output=/boot/grub/grub.cfg
else
    printf '%s\n' 'Unsupported GRUB layout; no changes made.' >&2
    exit 1
fi
checkCommandRequirements "$generator $checker"
# Debian drop-ins may override /etc/default/grub. Do not silently report success.
for fragment in /etc/default/grub.d/*.cfg; do
    [ -f "$fragment" ] || continue
    if grep -Eq '^[[:space:]]*(export[[:space:]]+)?GRUB_CMDLINE_LINUX(_DEFAULT)?=' "$fragment"; then
        printf 'Kernel arguments in %s override /etc/default/grub. Adjust that drop-in first; no changes made.\n' "$fragment" >&2
        exit 1
    fi
done
hook_file=''
if [ "$tool" = 'mkinitcpio -P' ] && [ -f /etc/mkinitcpio.conf ]; then
    hook_file=/etc/mkinitcpio.conf
    for fragment in /etc/mkinitcpio.conf.d/*.conf; do
        [ -f "$fragment" ] || continue
        if grep -Eq '^[[:space:]]*HOOKS=' "$fragment"; then
            printf 'The HOOKS in %s override /etc/mkinitcpio.conf. Add the plymouth hook there yourself; no changes made.\n' "$fragment" >&2
            exit 1
        fi
    done
fi

work=$(mktemp -d)
new_menu=''
config_pending=false
defaults_backup=''
cleanup_boot_splash() {
    if [ "$config_pending" = true ]; then
        "$ESCALATION_TOOL" cp -a -- "$defaults_backup" /etc/default/grub
        printf '%s\n' 'GRUB generation failed or was interrupted. Previous defaults restored; existing boot menu preserved.' >&2
    fi
    if [ -n "$new_menu" ]; then
        "$ESCALATION_TOOL" rm -f -- "$new_menu"
    fi
    rm -rf "$work"
}
trap cleanup_boot_splash 0
trap 'exit 130' INT
trap 'exit 143' TERM

# Install new kernel arguments and regenerate the menu, keeping the old menu
# until the new one passes its syntax check.
apply_kernel_arguments() {
    python3 ./configure.py grub-cmdline /etc/default/grub "$@" > "$work/defaults"
    if cmp -s "$work/defaults" /etc/default/grub; then
        printf '%s\n' 'Kernel arguments already as requested; GRUB menu unchanged.'
        return 0
    fi
    backup_system /etc/default/grub
    defaults_backup=$backup
    backup_system "$output"
    new_menu=$("$ESCALATION_TOOL" mktemp "$(dirname "$output")/.commander-grub.XXXXXX")
    config_pending=true
    "$ESCALATION_TOOL" install -m 644 "$work/defaults" /etc/default/grub
    "$ESCALATION_TOOL" "$generator" -o "$new_menu"
    "$ESCALATION_TOOL" "$checker" "$new_menu"
    "$ESCALATION_TOOL" mv -f -- "$new_menu" "$output"
    new_menu=''
    config_pending=false
}

if [ "$action" = on ]; then
    case "$PACKAGER" in
        apt-get | nala) packages='plymouth plymouth-themes' ;;
        *) packages=plymouth ;;
    esac
    hook_note=''
    [ -n "$hook_file" ] && hook_note=", add the plymouth hook to $hook_file"
    confirm "Install $packages, add 'splash' to the kernel command line in /etc/default/grub$hook_note, regenerate the GRUB menu and rebuild the boot images with '$tool'. Defaults, the boot menu and $hook_file are backed up first."
    # shellcheck disable=SC2086
    install_packages $packages
    if [ -n "$hook_file" ]; then
        python3 ./configure.py mkinitcpio-hooks "$hook_file" add > "$work/mkinitcpio.conf"
        if ! cmp -s "$work/mkinitcpio.conf" "$hook_file"; then
            backup_system "$hook_file"
            "$ESCALATION_TOOL" install -m 644 "$work/mkinitcpio.conf" "$hook_file"
        fi
    fi
    apply_kernel_arguments add splash
    if [ "$DTYPE" = fedora ] && command_exists grubby; then
        # Fedora's boot entries carry their own arguments, which grubby maintains.
        "$ESCALATION_TOOL" grubby --update-kernel=ALL --args=splash
    fi
    rebuild_initramfs
    printf '%s\n' 'Boot splash enabled from the next reboot. Pick a theme with the Boot Splash Theme entry.'
else
    confirm "Remove 'splash' and 'rhgb' from the kernel command line in /etc/default/grub and regenerate the GRUB menu, so the system boots with text output. Plymouth, its themes and its boot image hook stay installed. Defaults and the boot menu are backed up first."
    apply_kernel_arguments remove splash rhgb
    if [ "$DTYPE" = fedora ] && command_exists grubby; then
        "$ESCALATION_TOOL" grubby --update-kernel=ALL --remove-args='splash rhgb'
    fi
    printf '%s\n' 'Boot splash disabled from the next reboot.'
fi

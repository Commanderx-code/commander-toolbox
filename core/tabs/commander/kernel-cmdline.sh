#!/bin/sh -e
# Shared GRUB kernel command line transaction, sourced after common.sh.
#
# grub_cmdline_setup MESSAGE  finds the GRUB layout and refuses drop-ins that
#                             override /etc/default/grub; MESSAGE explains what
#                             to do without GRUB.
# grub_cmdline_apply ACTION WORD...  edits GRUB_CMDLINE_LINUX_DEFAULT, generates
#                             the menu into a temporary file, syntax-checks it
#                             and only then replaces the live menu.
# grub_cmdline_cleanup        restores the previous defaults after a failure;
#                             callers run it from their exit trap.

grub_work=''
grub_new_menu=''
grub_config_pending=false
grub_defaults_backup=''

grub_cmdline_setup() {
    if [ ! -f /etc/default/grub ]; then
        printf '%s\n' "$1" >&2
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
    grub_work=$(mktemp -d)
}

grub_cmdline_cleanup() {
    if [ "$grub_config_pending" = true ]; then
        "$ESCALATION_TOOL" cp -a -- "$grub_defaults_backup" /etc/default/grub
        printf '%s\n' 'GRUB generation failed or was interrupted. Previous defaults restored; existing boot menu preserved.' >&2
    fi
    if [ -n "$grub_new_menu" ]; then
        "$ESCALATION_TOOL" rm -f -- "$grub_new_menu"
    fi
    if [ -n "$grub_work" ]; then
        rm -rf "$grub_work"
    fi
}

grub_cmdline_apply() {
    python3 ./configure.py grub-cmdline /etc/default/grub "$@" > "$grub_work/defaults"
    if cmp -s "$grub_work/defaults" /etc/default/grub; then
        printf '%s\n' 'Kernel arguments already as requested; GRUB menu unchanged.'
        return 0
    fi
    backup_system /etc/default/grub
    # backup_system, from common.sh, leaves the copy's path in backup.
    # shellcheck disable=SC2154
    grub_defaults_backup=$backup
    backup_system "$output"
    grub_new_menu=$("$ESCALATION_TOOL" mktemp "$(dirname "$output")/.commander-grub.XXXXXX")
    grub_config_pending=true
    "$ESCALATION_TOOL" install -m 644 "$grub_work/defaults" /etc/default/grub
    "$ESCALATION_TOOL" "$generator" -o "$grub_new_menu"
    "$ESCALATION_TOOL" "$checker" "$grub_new_menu"
    "$ESCALATION_TOOL" mv -f -- "$grub_new_menu" "$output"
    grub_new_menu=''
    grub_config_pending=false
}

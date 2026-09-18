#!/bin/sh -e
# Sourced by resolve.sh after environment setup and installation confirmation.
resolve_apt_nvidia() {
    if [ ! -e /etc/apt/sources.list.d/nvidia-container-toolkit.list ] &&
        [ ! -e /etc/apt/sources.list.d/commander-nvidia-container-toolkit.list ]; then
        confirm 'Add the official NVIDIA Container Toolkit APT repository with a dedicated signing key?'
        install_packages ca-certificates curl gnupg
        repo_work=$(mktemp -d)
        trap 'rm -rf -- "$repo_work"' 0
        curl -fLsS https://nvidia.github.io/libnvidia-container/gpgkey -o "$repo_work/key.asc"
        gpg --batch --dearmor --output "$repo_work/key.gpg" "$repo_work/key.asc"
        curl -fLsS https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list -o "$repo_work/list"
        sed 's#deb https://#deb [signed-by=/usr/share/keyrings/commander-nvidia-container-toolkit.gpg] https://#' \
            "$repo_work/list" > "$repo_work/signed.list"
        grep -q '^deb \[signed-by=/usr/share/keyrings/commander-nvidia-container-toolkit.gpg\] https://' "$repo_work/signed.list"
        backup_system /usr/share/keyrings/commander-nvidia-container-toolkit.gpg
        "$ESCALATION_TOOL" install -m 644 "$repo_work/key.gpg" /usr/share/keyrings/commander-nvidia-container-toolkit.gpg
        "$ESCALATION_TOOL" install -m 644 "$repo_work/signed.list" /etc/apt/sources.list.d/commander-nvidia-container-toolkit.list
        rm -rf -- "$repo_work"
        trap - 0
    fi
    "$ESCALATION_TOOL" apt-get update
}

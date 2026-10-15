#!/bin/sh -e

# Run Commander Toolbox: from source when this is a checkout with Cargo,
# otherwise the latest published Linux x86_64 release, checked against its
# published SHA-256 sum. Prevent execution if only partially downloaded.
{
rc='\033[0m'
red='\033[0;31m'

check() {
    exit_code=$1
    message=$2

    if [ "$exit_code" -ne 0 ]; then
        printf '%sERROR: %s%s\n' "$red" "$message" "$rc"
        exit 1
    fi

    unset exit_code
    unset message
}

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$SCRIPT_DIR/Cargo.toml" ] && command -v cargo >/dev/null 2>&1; then
    TARGET_DIR=${CARGO_TARGET_DIR:-"$HOME/.cache/commander-toolbox/target"}
    mkdir -p "$TARGET_DIR"
    check $? "Preparing build cache"

    cd "$SCRIPT_DIR"
    check $? "Entering the toolbox directory"

    CARGO_TARGET_DIR="$TARGET_DIR" cargo run --locked -p linutil_tui --bin commander-toolbox -- "$@"
    check $? "Running Commander Toolbox from source"
    exit 0
fi

case "$(uname -m)" in
    x86_64|amd64) ;;
    *) check 1 "Releases are built for Linux x86_64 only; build from a checkout with cargo on this machine" ;;
esac

base=${COMMANDER_TOOLBOX_RELEASE:-https://github.com/Commanderx-code/commander-toolbox/releases/latest/download}
asset=commander-toolbox-linux-x86_64
work=$(mktemp -d)
check $? "Creating the temporary directory"
trap 'rm -rf "$work"' 0

curl --fail --silent --location --proto '=https' --tlsv1.2 -o "$work/SHA256SUMS" "$base/SHA256SUMS"
check $? "Downloading the Commander Toolbox checksums"
curl --fail --silent --location --proto '=https' --tlsv1.2 -o "$work/$asset" "$base/$asset"
check $? "Downloading Commander Toolbox"

expected=$(grep -E "^[0-9a-f]{64} [ *]?$asset\$" "$work/SHA256SUMS" | cut -c1-64)
if [ -z "$expected" ]; then
    check 1 "Finding $asset in the published checksums"
fi
actual=$(sha256sum -- "$work/$asset" | cut -c1-64)
if [ "$actual" != "$expected" ]; then
    check 1 "The downloaded Commander Toolbox does not match its published checksum"
fi

chmod +x "$work/$asset"
check $? "Making Commander Toolbox executable"

"$work/$asset" "$@"
check $? "Executing Commander Toolbox"
} # End of wrapping

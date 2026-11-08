#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULE_FILE="$SCRIPT_DIR/udev/99-e2v-octoplus.rules"
DEST_FILE="/etc/udev/rules.d/99-e2v-octoplus.rules"

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run as root: sudo $0"
    exit 1
fi

echo "[*] Copying udev rule from $RULE_FILE to $DEST_FILE..."
cp "$RULE_FILE" "$DEST_FILE"
chmod 644 "$DEST_FILE"

echo "[*] Reloading and triggering udev rules..."
udevadm control --reload-rules
udevadm trigger

echo "[+] Done! e2v OctoPlus cameras are now accessible without sudo."

#!/bin/bash
set -euo pipefail

BACKUP_USER="${1:-backup}"
BACKUP_DIR="${2:-/mnt/remote-backups}"
AUTHORIZED_KEY="${3:-}"

if [[ $EUID -ne 0 ]]; then
    echo "Must run as root on the backup server." >&2
    exit 1
fi

echo "Setting up backup receiver on this machine..."

if ! id "$BACKUP_USER" &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$BACKUP_DIR" "$BACKUP_USER"
    echo "Created user: $BACKUP_USER"
fi

mkdir -p "$BACKUP_DIR"
chown "$BACKUP_USER:$BACKUP_USER" "$BACKUP_DIR"

if [[ -n "$AUTHORIZED_KEY" ]]; then
    SSH_DIR="/home/$BACKUP_USER/.ssh"
    mkdir -p "$SSH_DIR"
    echo "$AUTHORIZED_KEY" >> "$SSH_DIR/authorized_keys"
    chmod 700 "$SSH_DIR"
    chmod 600 "$SSH_DIR/authorized_keys"
    chown -R "$BACKUP_USER:$BACKUP_USER" "$SSH_DIR"
    echo "SSH key added for $BACKUP_USER."
fi

SUDOERS_LINE="$BACKUP_USER ALL=(root) NOPASSWD: /usr/bin/btrfs receive $BACKUP_DIR, /usr/bin/btrfs subvolume delete $BACKUP_DIR/*, /usr/bin/btrfs subvolume list *"
chmod 440 "/etc/sudoers.d/btrfs-snapshot-sync"

echo ""
echo "Remote setup complete."
echo "  Backup user : $BACKUP_USER"
echo "  Backup dir  : $BACKUP_DIR"
echo ""
echo "In your config.json on the source machine, set:"
echo "  remote.user = \"$BACKUP_USER\""
echo "  remote.backup_dir = \"$BACKUP_DIR\""
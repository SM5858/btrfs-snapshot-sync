# btrfs-snapshot-sync

Automated backup system for Linux using Btrfs snapshots. Creates hourly point-in-time snapshots of a Btrfs subvolume, sends them to a remote machine over SSH using `btrfs send/receive`, and enforces a retention policy to prevent unlimited disk growth.

## How it works

1. **Snapshot** — every hour, a read-only Btrfs snapshot is created of the configured subvolume. Btrfs copy-on-write means only changed data consumes extra space.
2. **Transfer** — the snapshot is streamed to a backup server via `btrfs send | ssh | btrfs receive`. Subsequent transfers are incremental: only the delta since the last snapshot is sent.
3. **Retention** — old snapshots are pruned on both machines according to the policy in config (hourly, daily, weekly, monthly tiers).

If the main machine is lost, you can restore from the latest snapshot on the backup server.

## Requirements

- Linux with a Btrfs filesystem
- `btrfs-progs` installed on both machines
- Python 3.8+
- SSH access from the source machine to the backup server (key-based auth)
- Root access (btrfs operations require root)

## Installation

```bash
git clone https://github.com/onxxdatas/btrfs-snapshot-sync
cd btrfs-snapshot-sync
sudo bash scripts/install.sh
```

The installer copies only the runtime files (`btrfs_backup.py` and `src/`) to
`/opt/btrfs-snapshot-sync` — the repository itself, tests and `.git` are not
installed. If you forked the project, clone your own fork instead.

On the **backup server**, run:

```bash
sudo bash scripts/setup_remote.sh backup /mnt/remote-backups
```

## Configuration

After installation, edit `/etc/btrfs-snapshot-sync/config.json`:

```json
{
  "source_subvolume": "/",
  "snapshot_dir": "/mnt/snapshots",
  "snapshot_prefix": "backup",
  "retention": {
    "keep_hourly": 24,
    "keep_daily": 7,
    "keep_weekly": 4,
    "keep_monthly": 3
  },
  "transfer": {
    "enabled": true
  },
  "remote": {
    "host": "backup-server.example.com",
    "user": "backup",
    "port": 22,
    "backup_dir": "/mnt/remote-backups",
    "ssh_key": "/root/.ssh/backup_id_ed25519"
  }
}
```

### SSH key setup

```bash
ssh-keygen -t ed25519 -f /root/.ssh/backup_id_ed25519 -N ""
ssh-copy-id -i /root/.ssh/backup_id_ed25519.pub backup@backup-server.example.com
```

## Enabling the timer

```bash
systemctl enable --now btrfs-snapshot-sync.timer
systemctl list-timers btrfs-snapshot-sync.timer
```

## Manual usage

```bash
btrfs-snapshot-sync run              # full cycle: snapshot + send + cull
btrfs-snapshot-sync snapshot         # create a local snapshot only
btrfs-snapshot-sync list             # list local snapshots
btrfs-snapshot-sync cull --dry-run   # preview what retention would delete
btrfs-snapshot-sync send             # send latest snapshot to remote
btrfs-snapshot-sync init-config      # write a default config file
```

## Recovery

On the backup server, to restore a snapshot to a new disk:

```bash
# Mount the new disk
mount /dev/sdX /mnt/restore

# Send the snapshot back
btrfs send /mnt/remote-backups/backup_20240601_120000 | btrfs receive /mnt/restore

# The subvolume is at /mnt/restore/backup_20240601_120000
# Set it as the default subvolume if restoring a root filesystem
btrfs subvolume set-default /mnt/restore/backup_20240601_120000
```

## Project structure

```
btrfs-snapshot-sync/
├── btrfs_backup.py        # CLI entry point
├── src/
│   ├── __init__.py
│   ├── backup.py          # orchestrator
│   ├── snapshot.py        # local snapshot management
│   ├── transfer.py        # remote send/receive over SSH
│   ├── retention.py       # retention policy
│   └── config.py          # config loading and validation
├── config/
│   └── config.json        # default config template
├── systemd/
│   ├── btrfs-snapshot-sync.service
│   └── btrfs-snapshot-sync.timer
├── scripts/
│   ├── install.sh         # installs on source machine
│   └── setup_remote.sh    # configures backup server
├── tests/
│   ├── test_retention.py
│   └── test_config.py
└── requirements.txt
```

## Running tests

```bash
pip install -r requirements.txt
pytest tests/
```

## Limitations

- Changes made after the last successful sync are not recoverable.
- The source subvolume must be on a Btrfs filesystem.
- The backup directory on the remote machine must also be on a Btrfs filesystem.
- All operations run as root.
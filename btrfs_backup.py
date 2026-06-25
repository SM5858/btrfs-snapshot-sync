#!/usr/bin/env python3

import argparse
import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.backup import BackupRunner, setup_logging
from src.config import load_config, validate_config, DEFAULT_CONFIG
from src.snapshot import SnapshotManager
from src.transfer import RemoteTransfer
from src.retention import RetentionPolicy


def cmd_run(args):
    runner = BackupRunner(config_path=args.config)
    success = runner.run()
    sys.exit(0 if success else 1)


def cmd_snapshot(args):
    config = load_config(args.config)
    setup_logging(config)
    mgr = SnapshotManager(config)
    path = mgr.create_snapshot()
    print(f"Created: {path}")


def cmd_list(args):
    config = load_config(args.config)
    mgr = SnapshotManager(config)
    snapshots = mgr.list_snapshots()
    if not snapshots:
        print("No snapshots found.")
        return
    for s in snapshots:
        print(s)


def cmd_cull(args):
    config = load_config(args.config)
    setup_logging(config)
    mgr = SnapshotManager(config)
    retention = RetentionPolicy(config)
    prefix = config["snapshot_prefix"]

    snapshots = mgr.list_snapshots()
    to_delete = retention.select_snapshots_to_delete(snapshots, prefix)

    if not to_delete:
        print("Nothing to delete.")
        return

    for path in to_delete:
        if args.dry_run:
            print(f"Would delete: {path}")
        else:
            mgr.delete_snapshot(path)
            print(f"Deleted: {path}")


def cmd_send(args):
    config = load_config(args.config)
    setup_logging(config)

    mgr = SnapshotManager(config)
    transfer = RemoteTransfer(config)

    if args.snapshot:
        snapshot_path = Path(args.snapshot)
    else:
        snapshot_path = mgr.get_latest_snapshot()
        if not snapshot_path:
            print("No snapshots found to send.")
            sys.exit(1)

    parent = Path(args.parent) if args.parent else None
    transfer.ensure_remote_dir()
    transfer.send_snapshot(snapshot_path, parent_path=parent)
    print(f"Sent: {snapshot_path.name}")


def cmd_init_config(args):
    dest = Path(args.output or "config/config.json")
    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(dest, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    print(f"Default config written to: {dest}")
    print("Edit it and set at minimum: source_subvolume, snapshot_dir, remote.host, remote.user")


def main():
    parser = argparse.ArgumentParser(
        prog="btrfs-snapshot-sync",
        description="Automated Btrfs snapshot backup system"
    )
    parser.add_argument("-c", "--config", metavar="PATH", help="Path to config file")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="Run a full backup cycle (snapshot + send + cull)")

    sub.add_parser("snapshot", help="Create a local snapshot only")

    sub.add_parser("list", help="List local snapshots")

    cull_p = sub.add_parser("cull", help="Apply retention policy to local snapshots")
    cull_p.add_argument("--dry-run", action="store_true", help="Show what would be deleted")

    send_p = sub.add_parser("send", help="Send a snapshot to the remote machine")
    send_p.add_argument("--snapshot", metavar="PATH", help="Snapshot path to send (default: latest)")
    send_p.add_argument("--parent", metavar="PATH", help="Parent snapshot for incremental send")

    init_p = sub.add_parser("init-config", help="Write a default config file")
    init_p.add_argument("-o", "--output", metavar="PATH", help="Output path (default: config/config.json)")

    args = parser.parse_args()

    dispatch = {
        "run": cmd_run,
        "snapshot": cmd_snapshot,
        "list": cmd_list,
        "cull": cmd_cull,
        "send": cmd_send,
        "init-config": cmd_init_config,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()

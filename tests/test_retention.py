import pytest
from datetime import datetime, timedelta
from src.retention import RetentionPolicy, parse_snapshot_time

PREFIX = "backup"

def make_name(dt):
    return f"{PREFIX}_{dt.strftime('%Y%m%d_%H%M%S')}"

def make_range(start, count, delta):
    return [make_name(start + delta * i) for i in range(count)]


def test_parse_snapshot_time():
    name = "backup_20240101_120000"
    ts = parse_snapshot_time(name, PREFIX)
    assert ts == datetime(2024, 1, 1, 12, 0, 0)


def test_parse_invalid_returns_none():
    assert parse_snapshot_time("backup_garbage", PREFIX) is None
    assert parse_snapshot_time("other_20240101_120000", PREFIX) is None


def test_keep_hourly():
    config = {"retention": {"keep_hourly": 5, "keep_daily": 0, "keep_weekly": 0, "keep_monthly": 0}}
    policy = RetentionPolicy(config)

    now = datetime(2024, 6, 1, 12, 0, 0)
    snaps = make_range(now - timedelta(hours=10), 11, timedelta(hours=1))

    to_delete = policy.select_snapshots_to_delete(snaps, PREFIX)

    kept = set(snaps) - set(to_delete)
    assert len(kept) == 5
    assert make_name(now - timedelta(hours=4)) in kept
    assert make_name(now) in kept


def test_nothing_to_delete_when_few_snapshots():
    config = {"retention": {"keep_hourly": 24, "keep_daily": 7, "keep_weekly": 4, "keep_monthly": 3}}
    policy = RetentionPolicy(config)

    now = datetime(2024, 6, 1, 12, 0, 0)
    snaps = make_range(now - timedelta(hours=3), 4, timedelta(hours=1))

    to_delete = policy.select_snapshots_to_delete(snaps, PREFIX)
    assert to_delete == []


def test_empty_list():
    policy = RetentionPolicy({})
    result = policy.select_snapshots_to_delete([], PREFIX)
    assert result == []


def test_daily_deduplication():
    config = {"retention": {"keep_hourly": 1, "keep_daily": 3, "keep_weekly": 0, "keep_monthly": 0}}
    policy = RetentionPolicy(config)

    now = datetime(2024, 6, 5, 12, 0, 0)
    snaps = []
    for day in range(5):
        base = now - timedelta(days=day + 1)
        for hour in range(4):
            snaps.append(make_name(base + timedelta(hours=hour)))

    snaps.append(make_name(now))
    snaps.sort()

    to_delete = policy.select_snapshots_to_delete(snaps, PREFIX)
    kept = set(snaps) - set(to_delete)

    day_keys = set()
    for name in kept:
        ts = parse_snapshot_time(name, PREFIX)
        if ts:
            day_keys.add(ts.strftime("%Y%m%d"))

    assert len(day_keys) <= 4

import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def parse_snapshot_time(name, prefix):
    expected_start = prefix + "_"
    if not name.startswith(expected_start):
        return None
    suffix = name[len(expected_start):]
    try:
        return datetime.strptime(suffix, TIMESTAMP_FORMAT)
    except ValueError:
        return None


class RetentionPolicy:
    def __init__(self, config):
        retention = config.get("retention", {})
        self.keep_hourly = retention.get("keep_hourly", 24)
        self.keep_daily = retention.get("keep_daily", 7)
        self.keep_weekly = retention.get("keep_weekly", 4)
        self.keep_monthly = retention.get("keep_monthly", 3)

    def select_snapshots_to_delete(self, snapshots, prefix):
        parsed = []
        for s in snapshots:
            name = Path(s).name if not isinstance(s, str) else s
            ts = parse_snapshot_time(name, prefix)
            if ts:
                parsed.append((ts, s))

        if not parsed:
            return []

        parsed.sort(key=lambda x: x[0])
        now = parsed[-1][0]

        keep = set()

        hourly_snaps = list(reversed(parsed))
        for ts, snap in hourly_snaps[:self.keep_hourly]:
            keep.add(snap)

        remaining = hourly_snaps[self.keep_hourly:]

        daily_cutoff = now - timedelta(days=self.keep_daily)
        weekly_cutoff = now - timedelta(weeks=self.keep_weekly)
        monthly_cutoff = now - timedelta(days=self.keep_monthly * 30)

        seen_days = set()
        seen_weeks = set()
        seen_months = set()

        for ts, snap in remaining:
            day_key = ts.strftime("%Y%m%d")
            if ts >= daily_cutoff and day_key not in seen_days:
                keep.add(snap)
                seen_days.add(day_key)
                continue

            week_key = ts.strftime("%Y_W%W")
            if ts >= weekly_cutoff and week_key not in seen_weeks:
                keep.add(snap)
                seen_weeks.add(week_key)
                continue

            month_key = ts.strftime("%Y%m")
            if ts >= monthly_cutoff and month_key not in seen_months:
                keep.add(snap)
                seen_months.add(month_key)
                continue

        to_delete = [s for _, s in parsed if s not in keep]
        logger.info(
            "Retention: keeping %d of %d snapshots, deleting %d",
            len(keep), len(parsed), len(to_delete)
        )
        return to_delete

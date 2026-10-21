"""Daisy/ALP chronological coordinates, matching date +%Y/%W/%w."""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def archive_date(instant=None):
    if instant is None:
        instant = datetime.now(timezone.utc)
    zone_name = os.environ.get("FILEPROXY_TIMEZONE", "").strip()
    if zone_name:
        try:
            local = instant.astimezone(ZoneInfo(zone_name))
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Invalid FILEPROXY_TIMEZONE: " + zone_name) from exc
    else:
        local = instant.astimezone()
    return {
        "year": int(local.strftime("%Y")),
        "week": int(local.strftime("%W")),
        "weekday": int(local.strftime("%w")),
        "localDate": local.strftime("%Y-%m-%d"),
        "timezone": zone_name or str(local.tzinfo),
        "dateConvention": "ALP-Ww:%Y/%W/%w",
    }

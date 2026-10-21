"""Daisy canonical ISO week coordinates, with an ALP compatibility comparison."""
from datetime import datetime, timezone
import os
from zoneinfo import ZoneInfo

def daisy_date(instant=None):
    moment = instant or datetime.now(timezone.utc)
    zone = os.environ.get("FILEPROXY_TIMEZONE", "")
    local = moment.astimezone(ZoneInfo(zone)) if zone else moment.astimezone()
    year, week, day = local.isocalendar()
    return {"year": year, "week": week, "weekday": day,
            "wwd": f"{week:02d}{day}", "path": f"{year}/{week:02d}{day}",
            "localDate": local.date().isoformat(),
            "timezone": zone or str(local.tzinfo),
            "convention": "DAISY:%G/%V/%u",
            "legacy": {"year": int(local.strftime("%Y")),
                       "week": int(local.strftime("%W")),
                       "weekday": int(local.strftime("%w")),
                       "convention": "ALP:%Y/%W/%w"}}

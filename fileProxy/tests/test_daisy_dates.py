from datetime import datetime, timezone
import os
from unittest import TestCase
from unittest.mock import patch
from fileproxy.daisy_dates import daisy_date


class DaisyDateTests(TestCase):
    def test_daisy_iso_date_is_not_alp_date(self):
        with patch.dict(os.environ, {"FILEPROXY_TIMEZONE": "America/Denver"}):
            value = daisy_date(datetime(2026, 10, 12, 18, tzinfo=timezone.utc))
        self.assertEqual((value["year"], value["week"], value["weekday"]), (2026, 42, 1))
        self.assertEqual((value["legacy"]["year"], value["legacy"]["week"],
                          value["legacy"]["weekday"]), (2026, 41, 1))

    def test_sunday_is_seven_not_zero(self):
        with patch.dict(os.environ, {"FILEPROXY_TIMEZONE": "America/Denver"}):
            value = daisy_date(datetime(2026, 10, 11, 18, tzinfo=timezone.utc))
        self.assertEqual(value["weekday"], 7)
        self.assertEqual(value["legacy"]["weekday"], 0)

    def test_iso_year_can_differ_from_calendar_year(self):
        with patch.dict(os.environ, {"FILEPROXY_TIMEZONE": "America/Denver"}):
            value = daisy_date(datetime(2027, 1, 1, 19, tzinfo=timezone.utc))
        self.assertEqual((value["year"], value["week"], value["weekday"]), (2026, 53, 5))
        self.assertEqual((value["legacy"]["year"], value["legacy"]["week"],
                          value["legacy"]["weekday"]), (2027, 0, 5))

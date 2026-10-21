import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from fileproxy.datepaths import archive_date


class DateTests(unittest.TestCase):
    def test_monday_and_sunday(self):
        with patch.dict(os.environ, {"FILEPROXY_TIMEZONE": "America/Denver"}):
            monday = archive_date(datetime(2026, 10, 12, 18, tzinfo=timezone.utc))
            sunday = archive_date(datetime(2026, 10, 11, 18, tzinfo=timezone.utc))
        self.assertEqual((monday["year"], monday["week"], monday["weekday"]), (2026, 41, 1))
        self.assertEqual((sunday["year"], sunday["week"], sunday["weekday"]), (2026, 40, 0))

    def test_week_zero(self):
        with patch.dict(os.environ, {"FILEPROXY_TIMEZONE": "America/Denver"}):
            value = archive_date(datetime(2027, 1, 1, 19, tzinfo=timezone.utc))
        self.assertEqual((value["year"], value["week"], value["weekday"]), (2027, 0, 5))


if __name__ == "__main__":
    unittest.main()

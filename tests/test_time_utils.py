import unittest
from datetime import time

from core.time_utils import parse_hhmm, time_to_hhmm


class TimeUtilsTests(unittest.TestCase):
    def test_parses_four_digit_time_without_colon(self):
        self.assertEqual(parse_hhmm(830), time(8, 30))
        self.assertEqual(parse_hhmm("1745"), time(17, 45))

    def test_accepts_midnight(self):
        self.assertEqual(parse_hhmm(0), time(0, 0))

    def test_rejects_invalid_hour_or_minute(self):
        self.assertIsNone(parse_hhmm(2360))
        self.assertIsNone(parse_hhmm(1260))
        self.assertIsNone(parse_hhmm("hora"))

    def test_formats_time_as_hhmm_number(self):
        self.assertEqual(time_to_hhmm(time(8, 5)), 805)
        self.assertEqual(time_to_hhmm(time(0, 0)), 0)


if __name__ == "__main__":
    unittest.main()

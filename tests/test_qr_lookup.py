import unittest
from unittest.mock import patch

from core.excel_utils import get_process_by_id
from core.qr_utils import extract_process_id, normalize_process_id


class QrUtilsTests(unittest.TestCase):
    def test_accepts_id_and_url(self):
        self.assertEqual(extract_process_id("000001"), "000001")
        self.assertEqual(extract_process_id("1"), "000001")
        self.assertEqual(
            extract_process_id(
                "https://formsmtech.streamlit.app/?processo_id=000029"
            ),
            "000029",
        )

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            extract_process_id("ABC123")
        with self.assertRaises(ValueError):
            extract_process_id("https://formsmtech.streamlit.app/")
        with self.assertRaises(ValueError):
            normalize_process_id("1234567")


class ProcessLookupTests(unittest.TestCase):
    rows = [
        {
            "CLIENTE": "JDE COFFEE",
            "ACABADO": "DISPLAY ARAMADO P PILÃO",
            "FERRAMENTAL": "Laser Tube",
            "PROCESSO": "15X15 Nest 1",
            "PROCESSO_ID": "000001",
        }
    ]

    @patch("core.excel_utils.load_process_data", return_value=rows)
    def test_finds_process_by_id(self, _load_data):
        result = get_process_by_id("1")
        self.assertEqual(result["processo_id"], "000001")
        self.assertEqual(result["cliente"], "JDE COFFEE")
        self.assertEqual(result["processo"], "15X15 Nest 1")

    @patch("core.excel_utils.load_process_data", return_value=rows)
    def test_returns_none_for_unknown_id(self, _load_data):
        self.assertIsNone(get_process_by_id("999999"))

    @patch("core.excel_utils.load_process_data", return_value=rows * 2)
    def test_rejects_duplicate_id(self, _load_data):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            get_process_by_id("000001")


if __name__ == "__main__":
    unittest.main()

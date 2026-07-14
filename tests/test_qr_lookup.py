import unittest
from unittest.mock import patch

from core.excel_utils import get_process_by_id
from core.qr_utils import extract_process_id, is_painting_process, normalize_process_id


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

    def test_identifies_painting_process(self):
        self.assertTrue(is_painting_process({"ferramental": " pintura "}))
        self.assertFalse(is_painting_process({"ferramental": "Solda MIG"}))
        self.assertFalse(is_painting_process(None))


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

    @patch("core.excel_utils.load_painting_process_data", return_value=[])
    @patch("core.excel_utils.load_process_data", return_value=rows)
    def test_finds_process_by_id(self, _load_data, _load_painting):
        result = get_process_by_id("1")
        self.assertEqual(result["processo_id"], "000001")
        self.assertEqual(result["cliente"], "JDE COFFEE")
        self.assertEqual(result["processo"], "15X15 Nest 1")

    @patch("core.excel_utils.load_painting_process_data", return_value=[])
    @patch("core.excel_utils.load_process_data", return_value=rows)
    def test_returns_none_for_unknown_id(self, _load_data, _load_painting):
        self.assertIsNone(get_process_by_id("999999"))

    @patch("core.excel_utils.load_painting_process_data", return_value=[])
    @patch("core.excel_utils.load_process_data", return_value=rows * 2)
    def test_rejects_duplicate_id(self, _load_data, _load_painting):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            get_process_by_id("000001")

    @patch(
        "core.excel_utils.load_painting_process_data",
        return_value=[
            {
                "CLIENTE": "JDE COFFEE",
                "ACABADO": "DISPLAY ARAMADO G",
                "FERRAMENTAL": "PINTURA",
                "PROCESSO": "CORPO ENVIO - VERMELHO",
                "PROCESSO_ID": "001123",
            }
        ],
    )
    @patch("core.excel_utils.load_process_data", return_value=[])
    def test_finds_painting_process_by_id(self, _load_data, _load_painting):
        result = get_process_by_id("1123")
        self.assertEqual(result["processo_id"], "001123")
        self.assertEqual(result["ferramental"], "PINTURA")


if __name__ == "__main__":
    unittest.main()

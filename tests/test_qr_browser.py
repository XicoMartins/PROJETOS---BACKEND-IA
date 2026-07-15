import unittest
from types import SimpleNamespace

from core.qr_browser import COMPONENT_DIR, extract_scanned_value


class QrBrowserTests(unittest.TestCase):
    def test_extracts_scanned_value_from_mapping(self):
        result = {"scanned": {"value": " 000038 ", "nonce": 123}}

        self.assertEqual(extract_scanned_value(result), "000038")

    def test_extracts_last_trigger_when_streamlit_returns_a_list(self):
        result = SimpleNamespace(
            scanned=[
                {"value": "000037", "nonce": 122},
                {"value": "000038", "nonce": 123},
            ]
        )

        self.assertEqual(extract_scanned_value(result), "000038")

    def test_returns_none_without_scan(self):
        self.assertIsNone(extract_scanned_value(None))
        self.assertIsNone(extract_scanned_value({}))

    def test_component_assets_are_bundled(self):
        for relative in ("scanner.html", "scanner.css", "dist/scanner.js"):
            path = COMPONENT_DIR / relative
            self.assertTrue(path.is_file(), relative)
            self.assertGreater(path.stat().st_size, 0, relative)


if __name__ == "__main__":
    unittest.main()

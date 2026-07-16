import unittest
from types import SimpleNamespace

from core.time_input import COMPONENT_DIR, extract_changed_value, safe_component_key


class TimeInputTests(unittest.TestCase):
    def test_extracts_confirmed_value(self):
        result = {"changed": {"value": "0830", "nonce": 1}}
        self.assertEqual(extract_changed_value(result), "0830")

    def test_extracts_last_trigger_value(self):
        result = SimpleNamespace(
            changed=[
                {"value": "0830", "nonce": 1},
                {"value": "1745", "nonce": 2},
            ]
        )
        self.assertEqual(extract_changed_value(result), "1745")

    def test_component_assets_exist(self):
        for filename in ("time_input.html", "time_input.css", "time_input.js"):
            self.assertTrue((COMPONENT_DIR / filename).is_file(), filename)

        html = (COMPONENT_DIR / "time_input.html").read_text(encoding="utf-8")
        self.assertIn('maxlength="5"', html)
        self.assertIn('placeholder="HH:MM"', html)

    def test_component_key_does_not_use_streamlit_event_separator(self):
        key = safe_component_key("form_field__0__hora_iniciada_hhmm")

        self.assertNotIn("__", key)
        self.assertEqual(key, safe_component_key("form_field__0__hora_iniciada_hhmm"))
        self.assertNotEqual(key, safe_component_key("form_field__0__hora_finalizada_hhmm"))


if __name__ == "__main__":
    unittest.main()

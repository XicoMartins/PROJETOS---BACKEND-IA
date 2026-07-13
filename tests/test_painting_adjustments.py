from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from core.db_utils import (
    ProductionDB,
    build_painting_entry_payload_from_streamlit,
)


class PaintingAdjustmentsTests(unittest.TestCase):
    def test_painting_entry_can_be_listed_and_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            db = ProductionDB(db_path=str(database_path), database_url=None)
            original = build_painting_entry_payload_from_streamlit(
                {
                    "cliente": "Cliente A",
                    "display": "Display A",
                    "numero_display": "12345678",
                    "codigo_pintura": "AZUL",
                    "ferramental": "Gancho 1",
                    "processo": "Pintura",
                    "data_producao": "13/07/26",
                    "hora_lancamento": "08:30",
                    "quantidade": 10,
                    "quantidade_total": 20,
                },
                "1.2",
                existing_entry={
                    "timestamp": "2026-07-13T08:30:00",
                    "schema_version": "1.2",
                },
            )
            hash_payload = {
                key: value for key, value in original.items() if key != "source_hash"
            }
            expected_hash_values = [
                "painting",
                *[str(hash_payload[key]) for key in sorted(hash_payload)],
            ]
            expected_hash = hashlib.sha256(
                "||".join(expected_hash_values).encode("utf-8")
            ).hexdigest()
            self.assertEqual(original["source_hash"], expected_hash)
            entry_id = db.save_painting_entry(original)

            entries = db.get_all_painting_entries()
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["codigo_pintura"], "AZUL")

            adjusted = build_painting_entry_payload_from_streamlit(
                {
                    "cliente": "Cliente A",
                    "display": "Display A",
                    "numero_display": "12345678",
                    "codigo_pintura": "PRETO",
                    "ferramental": "Gancho 2",
                    "processo": "Pintura final",
                    "data_producao": "14/07/26",
                    "hora_lancamento": "09:45",
                    "quantidade": 15,
                    "quantidade_total": 25,
                },
                "1.2",
                existing_entry=entries[0],
            )

            self.assertNotEqual(adjusted["source_hash"], original["source_hash"])
            self.assertEqual(adjusted["timestamp"], entries[0]["timestamp"])
            self.assertTrue(db.update_painting_entry(entry_id, adjusted))

            updated_entry = db.get_all_painting_entries()[0]
            self.assertEqual(updated_entry["codigo_pintura"], "PRETO")
            self.assertEqual(updated_entry["maquinario"], "Gancho 2")
            self.assertEqual(updated_entry["processo"], "Pintura final")
            self.assertEqual(updated_entry["quantidade"], 15)
            self.assertEqual(updated_entry["quantidade_total"], 25)
            self.assertEqual(db.get_all_entries(), [])


if __name__ == "__main__":
    unittest.main()

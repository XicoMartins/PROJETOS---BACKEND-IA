from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from core.db_utils import (
    ProductionDB,
    build_painting_entry_payload_from_streamlit,
)


class PaintingAdjustmentsTests(unittest.TestCase):
    def test_sqlite_upgrade_preserves_existing_painting_without_a_supplier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(database_path))
                with db.get_conn() as conn:
                    columns = conn.execute("PRAGMA table_info(painting_entries)")
                    if "fornecedor_pintura" in {row["name"] for row in columns}:
                        conn.execute("ALTER TABLE painting_entries DROP COLUMN fornecedor_pintura")
                    conn.execute("INSERT INTO painting_entries (cliente) VALUES ('Cliente antigo')")
                    conn.commit()
                reopened_db = ProductionDB(db_path=str(database_path))

            entry = reopened_db.get_all_painting_entries()[0]
            self.assertEqual(entry["cliente"], "Cliente antigo")
            self.assertIn("fornecedor_pintura", entry)
            self.assertIsNone(entry["fornecedor_pintura"])

    def test_painting_supplier_survives_creation_and_legacy_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(Path(temp_dir) / "production.db"))
            original = build_painting_entry_payload_from_streamlit(
                {"cliente": "Cliente A", "fornecedor_pintura": "SCHUNCK"}, "1.2"
            )
            entry_id = db.save_painting_entry(original)
            entry = db.get_all_painting_entries()[0]
            self.assertEqual(entry.get("fornecedor_pintura"), "SCHUNCK")

            adjusted = build_painting_entry_payload_from_streamlit(
                {"cliente": "Cliente A", "fornecedor_pintura": "Aquapint"},
                "1.2",
                existing_entry=entry,
            )
            self.assertNotEqual(adjusted["source_hash"], original["source_hash"])
            self.assertTrue(db.update_painting_entry(entry_id, adjusted))
            entry = db.get_all_painting_entries()[0]
            self.assertEqual(entry.get("fornecedor_pintura"), "Aquapint")

            legacy_adjustment = dict(entry)
            legacy_adjustment.pop("fornecedor_pintura")
            self.assertTrue(db.update_painting_entry(entry_id, legacy_adjustment))
            self.assertEqual(db.get_all_painting_entries()[0].get("fornecedor_pintura"), "Aquapint")

    def test_painting_form_requires_supplier_and_clears_it_for_each_qr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(Path(temp_dir) / "production.db"))
            process = {
                "processo_id": "001123",
                "acabado": "Display Teste",
                "ferramental": "Gancho para PINTURA",
                "processo": "Pintura final",
            }

            with (
                patch("core.db_utils._db_instance", db),
                patch("core.excel_utils.get_clientes", return_value=["Cliente Teste"]),
                patch("core.excel_utils.get_process_by_id", return_value=process),
                patch("core.qr_browser._component_renderer", return_value=lambda **_kwargs: None),
                patch("core.time_input.time_hhmm_component", return_value="0830"),
            ):
                app = AppTest.from_file("streamlit_app.py", default_timeout=90)
                app.session_state["auth_authenticated"] = True
                app.session_state["auth_user"] = "teste"
                app.run()
                supplier = app.selectbox(key="painting_form_field__0__fornecedor_pintura")
                self.assertIsNone(supplier.value)
                self.assertEqual(supplier.options, ["SCHUNCK", "Aquapint", "Multipint"])

                supplier.select("Aquapint").run()
                app.text_input(key="painting_qr_process_input").set_value("001123").run()
                self.assertTrue(
                    any("001123 identificado pelo QR Code" in message.value for message in app.success)
                )
                self.assertIsNone(app.selectbox(key="painting_form_field__0__fornecedor_pintura").value)

                app.selectbox(key="painting_form_field__0__cliente").select("Cliente Teste")
                app.text_input(key="painting_form_field__0__numero_display").set_value("12345678")
                app.text_input(key="painting_form_field__0__codigo_pintura").set_value("AZUL")
                app.button(key="save_painting_entry").click().run()
                self.assertTrue(any("Fornecedor de pintura" in message.value for message in app.error))
                self.assertEqual(db.get_all_painting_entries(), [])

                app.selectbox(key="painting_form_field__0__fornecedor_pintura").select("Multipint")
                app.button(key="save_painting_entry").click().run()
                entry = db.get_all_painting_entries()[0]
                self.assertEqual(entry.get("fornecedor_pintura"), "Multipint")
                self.assertIsNone(app.selectbox(key="painting_form_field__1__fornecedor_pintura").value)

                adjustment_key = f"painting_adjust_field__{entry['id']}"
                adjustment = app.selectbox(key=f"{adjustment_key}__fornecedor_pintura")
                self.assertEqual(adjustment.value, "Multipint")
                adjustment.select("SCHUNCK")
                app.button(key=f"{adjustment_key}__save_painting").click().run()
                self.assertEqual(db.get_all_painting_entries()[0].get("fornecedor_pintura"), "SCHUNCK")

                legacy_entry = dict(entry, source_hash=None)
                legacy_entry.pop("fornecedor_pintura")
                legacy_id = db.save_painting_entry(legacy_entry)
                app.run()
                app.selectbox(key="painting_adjust_selected_entry_id").select(legacy_id).run()
                legacy_key = f"painting_adjust_field__{legacy_id}"
                self.assertIsNone(app.selectbox(key=f"{legacy_key}__fornecedor_pintura").value)

                app.text_input(key=f"{legacy_key}__codigo_pintura").set_value("PRETO")
                app.button(key=f"{legacy_key}__save_painting").click().run()
                stored_legacy_entry = next(row for row in db.get_all_painting_entries() if row["id"] == legacy_id)
                self.assertEqual(stored_legacy_entry["codigo_pintura"], "PRETO")
                self.assertIsNone(stored_legacy_entry["fornecedor_pintura"])

                app.selectbox(key=f"{legacy_key}__fornecedor_pintura").select("Aquapint")
                app.button(key=f"{legacy_key}__save_painting").click().run()
                stored_legacy_entry = next(row for row in db.get_all_painting_entries() if row["id"] == legacy_id)
                self.assertEqual(stored_legacy_entry["fornecedor_pintura"], "Aquapint")

    def test_painting_entry_can_be_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(database_path), database_url=None)
            entry = build_painting_entry_payload_from_streamlit(
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
            )
            entry_id = db.save_painting_entry(entry)

            self.assertTrue(db.delete_painting_entry(entry_id))
            self.assertEqual(db.get_all_painting_entries(), [])

    def test_painting_entry_can_be_listed_and_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            with patch("core.db_utils.get_database_url", return_value=None):
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

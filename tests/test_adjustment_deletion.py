from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import core.db_utils as db_utils
from core.db_utils import (
    ProductionDB,
    build_entry_payload_from_streamlit,
    build_painting_entry_payload_from_streamlit,
)


class AdjustmentDeletionTests(unittest.TestCase):
    def test_painting_entry_requires_confirmation_before_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(database_path), database_url=None)
            entry_id = db.save_painting_entry(
                build_painting_entry_payload_from_streamlit(
                    {
                        "cliente": "Cliente Teste",
                        "display": "Display Teste",
                        "numero_display": "12345678",
                        "codigo_pintura": "AZUL",
                        "ferramental": "Gancho Teste",
                        "processo": "Pintura Teste",
                        "data_producao": "21/08/26",
                        "hora_lancamento": "08:30",
                        "quantidade": 1,
                        "quantidade_total": 1,
                    },
                    "1.2",
                )
            )

            previous_db = db_utils._db_instance
            db_utils._db_instance = db
            try:
                neutral_component = lambda **_kwargs: None
                with (
                    patch(
                        "core.qr_browser._component_renderer",
                        return_value=neutral_component,
                    ),
                    patch(
                        "core.time_input._component_renderer",
                        return_value=neutral_component,
                    ),
                ):
                    app = AppTest.from_file("streamlit_app.py", default_timeout=90)
                    app.session_state["auth_authenticated"] = True
                    app.session_state["auth_user"] = "teste"
                    app.run(timeout=90)

                    delete_key = f"painting_adjust_field__{entry_id}__delete"
                    self.assertIn(delete_key, [button.key for button in app.button])
                    next(
                        button for button in app.button if button.key == delete_key
                    ).click().run(timeout=90)

                    self.assertEqual(len(db.get_all_painting_entries()), 1)
                    confirm_key = (
                        f"painting_adjust_field__{entry_id}__confirm_delete"
                    )
                    self.assertIn(confirm_key, [button.key for button in app.button])
                    next(
                        button for button in app.button if button.key == confirm_key
                    ).click().run(timeout=90)

                    self.assertEqual(db.get_all_painting_entries(), [])
                    self.assertTrue(
                        any(
                            f"Lançamento de pintura #{entry_id} excluído com sucesso."
                            in message.value
                            for message in app.success
                        )
                    )
            finally:
                db_utils._db_instance = previous_db

    def test_production_entry_requires_confirmation_before_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "production.db"
            with patch("core.db_utils.get_database_url", return_value=None):
                db = ProductionDB(db_path=str(database_path), database_url=None)
            entry_id = db.save_entry(
                build_entry_payload_from_streamlit(
                    {
                        "cliente": "Cliente Teste",
                        "acabado": "Display Teste",
                        "numero_display": "12345678",
                        "ferramental": "Ferramental Teste",
                        "processo": "Processo Teste",
                        "data_producao": "21/08/26",
                        "operadores": ["Operador Teste"],
                        "numero_operadores": 1,
                        "hora_iniciada": "08:00",
                        "hora_finalizada": "09:00",
                        "quantidade_produzida": 1,
                        "pecas_mortas": 0,
                        "quantidade_total": 1,
                    },
                    "1.2",
                )
            )

            previous_db = db_utils._db_instance
            db_utils._db_instance = db
            try:
                neutral_component = lambda **_kwargs: None
                with (
                    patch(
                        "core.qr_browser._component_renderer",
                        return_value=neutral_component,
                    ),
                    patch(
                        "core.time_input._component_renderer",
                        return_value=neutral_component,
                    ),
                ):
                    app = AppTest.from_file("streamlit_app.py", default_timeout=90)
                    app.session_state["auth_authenticated"] = True
                    app.session_state["auth_user"] = "teste"
                    app.run(timeout=90)

                    delete_key = f"adjust_field__{entry_id}__delete"
                    self.assertIn(delete_key, [button.key for button in app.button])
                    next(
                        button for button in app.button if button.key == delete_key
                    ).click().run(timeout=90)

                    self.assertEqual(len(db.get_all_entries()), 1)
                    confirm_key = f"adjust_field__{entry_id}__confirm_delete"
                    self.assertIn(confirm_key, [button.key for button in app.button])
                    next(
                        button for button in app.button if button.key == confirm_key
                    ).click().run(timeout=90)

                    self.assertEqual(db.get_all_entries(), [])
                    self.assertTrue(
                        any(
                            f"Lançamento #{entry_id} excluído com sucesso."
                            in message.value
                            for message in app.success
                        )
                    )
            finally:
                db_utils._db_instance = previous_db


if __name__ == "__main__":
    unittest.main()

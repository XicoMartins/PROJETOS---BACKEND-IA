import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from core.excel_utils import get_clientes


class ClientesTests(unittest.TestCase):
    def test_carrega_clientes_da_planilha_mestre_sem_duplicar(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.append(["CLIENTE"])
            worksheet.append(["Cliente B"])
            worksheet.append(["Cliente A"])
            worksheet.append(["Cliente B"])
            workbook.save(pasta / "CLIENTES.xlsx")

            with (
                patch("core.excel_utils.PLANILHAS_DIR", pasta),
                patch("core.excel_utils._CLIENTES_CACHE", None),
                patch("core.excel_utils._CLIENTES_CACHE_SIGNATURE", None),
            ):
                self.assertEqual(get_clientes(), ["Cliente A", "Cliente B"])


if __name__ == "__main__":
    unittest.main()

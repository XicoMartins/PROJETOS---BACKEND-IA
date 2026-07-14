import importlib.util
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gerar_qr_processos.py"
SPEC = importlib.util.spec_from_file_location("gerar_qr_processos", SCRIPT_PATH)
qr_processos = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(qr_processos)


class GeradorQrProcessosTests(unittest.TestCase):
    def criar_planilha(self, pasta: Path, ids=("000001", "000002")) -> Path:
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(
            ["CLIENTE", "ACABADO", "FERRAMENTAL", "PROCESSO", "PROCESSO_ID"]
        )
        for indice, processo_id in enumerate(ids, start=1):
            worksheet.append(
                ["Cliente", "Display", "Máquina", f"Processo {indice}", processo_id]
            )
        caminho = pasta / "processos.xlsx"
        workbook.save(caminho)
        return caminho

    def test_normaliza_id_para_seis_digitos(self):
        self.assertEqual(qr_processos.normalizar_processo_id(1), "000001")
        self.assertEqual(qr_processos.normalizar_processo_id("000029"), "000029")

    def test_rejeita_id_duplicado(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            arquivo = self.criar_planilha(pasta, ids=("000001", "000001"))
            with self.assertRaisesRegex(ValueError, "duplicado"):
                qr_processos.carregar_processos(arquivo)

    def test_gera_png_e_manifesto(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            arquivo = self.criar_planilha(pasta)
            saida = pasta / "qrs"

            manifesto = qr_processos.gerar_qrs(arquivo, saida)

            self.assertEqual(len(manifesto), 2)
            self.assertEqual(manifesto[0]["conteudo_qr"], "000001")
            self.assertEqual(len(list(saida.glob("*.png"))), 2)
            self.assertTrue((saida / "manifesto_qr.json").is_file())


if __name__ == "__main__":
    unittest.main()

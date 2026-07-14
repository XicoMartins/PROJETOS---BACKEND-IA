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

BASE_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gerar_qr_base.py"
BASE_SPEC = importlib.util.spec_from_file_location("gerar_qr_base", BASE_SCRIPT_PATH)
qr_base = importlib.util.module_from_spec(BASE_SPEC)
assert BASE_SPEC.loader is not None
BASE_SPEC.loader.exec_module(qr_base)


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

    def criar_planilha_nomeada(
        self,
        pasta: Path,
        nome: str,
        ids: tuple[str, ...],
    ) -> Path:
        caminho_original = self.criar_planilha(pasta, ids=ids)
        caminho = pasta / nome
        caminho_original.replace(caminho)
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

    def test_gera_base_com_varias_planilhas(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            self.criar_planilha_nomeada(pasta, "base_a.xlsx", ("000001", "000002"))
            self.criar_planilha_nomeada(pasta, "base_b.xlsx", ("000003",))
            saida = pasta / "qrs"

            manifesto = qr_base.gerar_qrs_da_base(pasta, saida)

            self.assertEqual(
                [item["processo_id"] for item in manifesto],
                ["000001", "000002", "000003"],
            )
            self.assertEqual(len(list(saida.rglob("*.png"))), 3)
            self.assertEqual(manifesto[2]["planilha"], "base_b.xlsx")
            self.assertEqual(manifesto[2]["pasta_qr"], "base_b")
            self.assertEqual(manifesto[2]["arquivo_qr"], "base_b/000003_PROCESSO_1.png")

    def test_rejeita_id_duplicado_entre_planilhas(self):
        with tempfile.TemporaryDirectory() as pasta_temporaria:
            pasta = Path(pasta_temporaria)
            self.criar_planilha_nomeada(pasta, "base_a.xlsx", ("000001",))
            self.criar_planilha_nomeada(pasta, "base_b.xlsx", ("000001",))

            with self.assertRaisesRegex(ValueError, "duplicado"):
                qr_base.carregar_base(pasta)


if __name__ == "__main__":
    unittest.main()

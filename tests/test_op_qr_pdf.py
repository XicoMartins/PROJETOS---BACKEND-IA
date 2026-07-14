import json
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    from core.op_qr_pdf import (
        AssociacaoOp,
        DadosOp,
        RegistroQr,
        aplicar_qrs_pdf,
        associar_op,
        carregar_manifesto,
        localizar_raiz_qr,
        validar_pdf_resultado,
        validar_qrs_associados,
    )
except ModuleNotFoundError as exc:
    Image = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, f"Dependências de PDF ausentes: {IMPORT_ERROR}")
class OpQrPdfTests(unittest.TestCase):
    def registro(self, processo_id, processo, ferramental="Laser Chapa"):
        return RegistroQr(
            processo_id=processo_id,
            cliente="Cliente",
            acabado="DISPLAY TESTE",
            ferramental=ferramental,
            processo=processo,
            arquivo_qr=f"qrs/{processo_id}.png",
        )

    def dados(self, operacao, marcados=None, ids=None):
        return DadosOp(
            arquivo=Path("001.pdf"),
            paginas=1,
            produto="DISPLAY TESTE",
            operacao=operacao,
            marcados=marcados or [],
            ids_existentes=ids or [],
        )

    def test_associa_intervalo_de_nests(self):
        registros = [
            self.registro("000001", "0,75 Nest 1"),
            self.registro("000002", "0,75 Nest 2"),
            self.registro("000003", "0,75 Nest 3"),
        ]

        resultado = associar_op(self.dados("0,75 Nest 1 - Nest 3"), registros)

        self.assertEqual(resultado.status, "ok")
        self.assertEqual(
            [item.processo_id for item in resultado.registros],
            ["000001", "000002", "000003"],
        )

    def test_associa_pintura_por_componente_movimento_e_cor(self):
        registros = [
            self.registro("001001", "CORPO ENVIO - VERMELHO", "PINTURA"),
            self.registro("001002", "CORPO RETORNO - VERMELHO", "PINTURA"),
        ]
        dados = self.dados(
            "Corpo - Produto - Vermelho",
            ["( X ) 26-Envio à Pintura"],
        )

        resultado = associar_op(dados, registros)

        self.assertEqual(resultado.status, "ok")
        self.assertEqual(resultado.registros[0].processo_id, "001001")

    def test_prioriza_id_ja_impresso_no_pdf(self):
        registros = [
            self.registro("000010", "Processo A"),
            self.registro("000011", "Processo B"),
        ]

        resultado = associar_op(
            self.dados("Título genérico", ids=["000011"]), registros
        )

        self.assertEqual(resultado.status, "ok")
        self.assertEqual(resultado.registros[0].processo_id, "000011")

    def test_aplica_qr_sem_alterar_tamanho_ou_paginas(self):
        with tempfile.TemporaryDirectory() as pasta_temp:
            pasta = Path(pasta_temp)
            origem = pasta / "op.pdf"
            destino = pasta / "resultado.pdf"
            qr = pasta / "qrs" / "000001.png"
            qr.parent.mkdir()
            Image.new("RGB", (120, 120), "black").save(qr)
            desenho = canvas.Canvas(str(origem), pagesize=(600, 800))
            desenho.drawString(30, 760, "ORDEM DE PRODUCAO")
            desenho.save()
            registro = self.registro("000001", "Processo")

            paginas = aplicar_qrs_pdf(origem, destino, [registro], pasta)

            original = PdfReader(origem)
            resultado = PdfReader(destino)
            self.assertEqual(paginas, 1)
            self.assertEqual(len(resultado.pages), len(original.pages))
            self.assertEqual(
                tuple(float(item) for item in resultado.pages[0].mediabox[2:]),
                tuple(float(item) for item in original.pages[0].mediabox[2:]),
            )
            self.assertIn("000001", resultado.pages[0].extract_text())
            validar_pdf_resultado(origem, destino, [registro])

    def test_localiza_manifesto_a_partir_de_subpasta(self):
        with tempfile.TemporaryDirectory() as pasta_temp:
            raiz = Path(pasta_temp)
            subpasta = raiz / "produto" / "processos"
            subpasta.mkdir(parents=True)
            (raiz / "manifesto_qr.json").write_text("[]", encoding="utf-8")

            self.assertEqual(localizar_raiz_qr(subpasta), raiz)

    def test_manifesto_nao_valida_todos_os_pngs_antecipadamente(self):
        with tempfile.TemporaryDirectory() as pasta_temp:
            raiz = Path(pasta_temp)
            manifesto = [
                {
                    "processo_id": "000001",
                    "cliente": "Cliente",
                    "acabado": "DISPLAY TESTE",
                    "ferramental": "Laser",
                    "processo": "Processo",
                    "arquivo_qr": "produto/000001.png",
                }
            ]
            (raiz / "manifesto_qr.json").write_text(
                json.dumps(manifesto), encoding="utf-8"
            )

            registros = carregar_manifesto(raiz)
            associacao = AssociacaoOp(
                self.dados("Processo"), registros, "ok", "Processo localizado"
            )

            self.assertEqual(len(registros), 1)
            with self.assertRaises(FileNotFoundError):
                validar_qrs_associados([associacao], raiz)


if __name__ == "__main__":
    unittest.main()

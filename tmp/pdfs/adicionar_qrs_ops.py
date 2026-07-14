from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


MAPEAMENTO_OPS: dict[str, list[str]] = {
    "005.pdf": ["000038", "000039"],
    "006.pdf": ["000040", "000041"],
    "007.pdf": ["000042", "000043", "000044"],
    "008.pdf": ["000045", "000046"],
    "009.pdf": ["000047", "000048", "000049"],
    "010.pdf": ["000050", "000051", "000052", "000053", "000054"],
    "012.pdf": ["000055", "000056"],
    "014.pdf": ["000057"],
    "015.pdf": ["000058"],
    "017.pdf": ["000060"],
    "019.pdf": ["000061"],
    "021.pdf": ["000063"],
    "022.pdf": ["000064"],
    "023.pdf": ["000065"],
    "024.pdf": ["000066"],
    "025.pdf": ["000067"],
    "026.pdf": ["000068"],
    "027.pdf": ["000069"],
    "028.pdf": ["000070"],
    "031.pdf": ["000073"],
    "032.pdf": ["000074"],
    "033.pdf": ["000075"],
    "034.pdf": ["000076"],
    "035.pdf": ["000077"],
    "036.pdf": ["000078"],
    "038.pdf": ["000080"],
    "039.pdf": ["000081"],
    "042.pdf": ["000082", "000083"],
    "043.pdf": ["000084", "000085"],
    "044.pdf": ["000086", "000087"],
    "045.pdf": [
        "000088",
        "000089",
        "000090",
        "000091",
        "000092",
        "000093",
        "000094",
        "000095",
        "000096",
        "000097",
    ],
    "047.pdf": ["001123"],
    "048.pdf": ["001133"],
    "049.pdf": ["001128"],
    "050.pdf": ["001138"],
    "051.pdf": ["001124"],
    "052.pdf": ["001134"],
    "053.pdf": ["001127"],
    "054.pdf": ["001137"],
    "055.pdf": ["001125"],
    "056.pdf": ["001135"],
    "057.pdf": ["001126"],
    "058.pdf": ["001136"],
    "059.pdf": ["001129"],
    "060.pdf": ["001139"],
    "061.pdf": ["001132"],
    "062.pdf": ["001142"],
    "063.pdf": ["001130"],
    "064.pdf": ["001140"],
    "065.pdf": ["001131"],
    "066.pdf": ["001141"],
}


def colunas_para(quantidade: int) -> int:
    if quantidade == 1:
        return 1
    if quantidade == 2:
        return 2
    if quantidade <= 6:
        return 3
    return 4


def texto_curto(texto: str, limite: int = 28) -> str:
    texto = " ".join(texto.strip().split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def criar_sobreposicao(
    largura: float,
    altura: float,
    registros: list[dict],
    raiz_qr: Path,
) -> PdfReader:
    memoria = io.BytesIO()
    desenho = canvas.Canvas(memoria, pagesize=(largura, altura))

    # Limites proporcionais da célula "IMAGEM DO PRODUTO" do formulário.
    x0, x1 = largura * 0.708, largura * 0.966
    y0, y1 = altura * 0.644, altura * 0.804
    margem = min(largura, altura) * 0.004
    x0 += margem
    x1 -= margem
    y0 += margem
    y1 -= margem

    desenho.setFillColorRGB(1, 1, 1)
    desenho.rect(x0, y0, x1 - x0, y1 - y0, fill=1, stroke=0)

    quantidade = len(registros)
    colunas = colunas_para(quantidade)
    linhas = math.ceil(quantidade / colunas)
    largura_celula = (x1 - x0) / colunas
    altura_celula = (y1 - y0) / linhas
    altura_rotulo = 16 if quantidade == 1 else 8
    tamanho_qr = min(
        largura_celula - 6,
        altura_celula - altura_rotulo - 5,
        94 if quantidade == 1 else 70,
    )

    for indice, registro in enumerate(registros):
        linha = indice // colunas
        coluna = indice % colunas
        centro_x = x0 + coluna * largura_celula + largura_celula / 2
        topo_celula = y1 - linha * altura_celula
        qr_x = centro_x - tamanho_qr / 2
        qr_y = topo_celula - tamanho_qr - 3
        caminho_qr = raiz_qr / registro["arquivo_qr"]
        desenho.drawImage(
            ImageReader(caminho_qr),
            qr_x,
            qr_y,
            width=tamanho_qr,
            height=tamanho_qr,
            preserveAspectRatio=True,
        )

        desenho.setFillColorRGB(0, 0, 0)
        fonte_id = 8 if quantidade == 1 else 5.5
        desenho.setFont("Helvetica-Bold", fonte_id)
        desenho.drawCentredString(centro_x, qr_y - fonte_id - 1, registro["processo_id"])
        if quantidade == 1:
            desenho.setFont("Helvetica", 5.8)
            desenho.drawCentredString(
                centro_x,
                qr_y - fonte_id - 8,
                texto_curto(registro["processo"]),
            )

    desenho.save()
    memoria.seek(0)
    return PdfReader(memoria)


def processar_pdf(
    origem: Path,
    destino: Path,
    registros: list[dict],
    raiz_qr: Path,
) -> int:
    leitor = PdfReader(origem)
    escritor = PdfWriter()
    for pagina_original in leitor.pages:
        if pagina_original.rotation:
            pagina_original.transfer_rotation_to_content()
        largura = float(pagina_original.mediabox.width)
        altura = float(pagina_original.mediabox.height)
        sobreposicao = criar_sobreposicao(largura, altura, registros, raiz_qr)
        pagina = PageObject.create_blank_page(width=largura, height=altura)
        pagina.merge_page(pagina_original)
        pagina.merge_page(sobreposicao.pages[0])
        escritor.add_page(pagina)

    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as arquivo:
        escritor.write(arquivo)
    return len(leitor.pages)


def main() -> int:
    pasta_ops = Path(sys.argv[1])
    raiz_qr = Path(sys.argv[2])
    manifesto_path = Path(sys.argv[3])
    pasta_saida = Path(sys.argv[4])
    relatorio_path = Path(sys.argv[5])

    manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
    por_id = {registro["processo_id"]: registro for registro in manifesto}
    pdfs_encontrados = {pdf.name for pdf in pasta_ops.glob("*.pdf")}
    if pdfs_encontrados != set(MAPEAMENTO_OPS):
        faltantes = sorted(set(MAPEAMENTO_OPS) - pdfs_encontrados)
        extras = sorted(pdfs_encontrados - set(MAPEAMENTO_OPS))
        raise ValueError(f"Conjunto de PDFs divergente. Faltantes={faltantes}; extras={extras}")

    relatorio = []
    for nome_pdf, ids in sorted(MAPEAMENTO_OPS.items()):
        registros = []
        for processo_id in ids:
            if processo_id not in por_id:
                raise ValueError(f"PROCESSO_ID ausente do manifesto: {processo_id}")
            registro = por_id[processo_id]
            caminho_qr = raiz_qr / registro["arquivo_qr"]
            if not caminho_qr.is_file():
                raise FileNotFoundError(f"QR Code não encontrado: {caminho_qr}")
            registros.append(registro)

        paginas = processar_pdf(
            pasta_ops / nome_pdf,
            pasta_saida / nome_pdf,
            registros,
            raiz_qr,
        )
        relatorio.append(
            {
                "pdf": nome_pdf,
                "paginas": paginas,
                "processos": [
                    {
                        "processo_id": item["processo_id"],
                        "ferramental": item["ferramental"],
                        "processo": item["processo"],
                    }
                    for item in registros
                ],
            }
        )

    relatorio_path.parent.mkdir(parents=True, exist_ok=True)
    relatorio_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "pdfs": len(relatorio),
                "paginas": sum(item["paginas"] for item in relatorio),
                "associacoes_qr": sum(len(item["processos"]) for item in relatorio),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

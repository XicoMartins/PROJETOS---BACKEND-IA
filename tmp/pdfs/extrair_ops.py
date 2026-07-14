from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pdfplumber


def extrair(pdf_path: Path) -> dict:
    with pdfplumber.open(pdf_path) as pdf:
        paginas = [pagina.extract_text() or "" for pagina in pdf.pages]
    texto = "\n".join(paginas)
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]

    titulo = ""
    for indice, linha in enumerate(linhas):
        if linha.lower().startswith("ordem de produ") and ":" in linha:
            if indice + 1 < len(linhas):
                titulo = linhas[indice + 1]
            break

    marcados = []
    for linha in linhas:
        if re.search(r"\(\s*[Xx]\s*\)", linha):
            marcados.append(linha)

    material = ""
    for indice, linha in enumerate(linhas):
        if linha.lower().startswith("descri") and "mat" in linha.lower():
            if indice + 1 < len(linhas):
                material = linhas[indice + 1]
            break

    return {
        "pdf": pdf_path.name,
        "paginas": len(paginas),
        "titulo_op": titulo,
        "marcados": marcados,
        "material_e_dados": material,
    }


def main() -> int:
    pasta = Path(sys.argv[1])
    saida = Path(sys.argv[2])
    registros = [extrair(pdf) for pdf in sorted(pasta.glob("*.pdf"))]
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(registros, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import sys
from pathlib import Path

from pypdf import PdfReader


def main() -> int:
    pasta_originais = Path(sys.argv[1])
    pasta_resultados = Path(sys.argv[2])
    relatorio_path = Path(sys.argv[3])
    saida_path = Path(sys.argv[4])
    mapeamento = json.loads(relatorio_path.read_text(encoding="utf-8"))

    resultado = []
    total_paginas = 0
    total_marcacoes = 0
    for item in mapeamento:
        nome = item["pdf"]
        original = PdfReader(pasta_originais / nome)
        modificado = PdfReader(pasta_resultados / nome)
        if len(original.pages) != len(modificado.pages):
            raise ValueError(f"{nome}: quantidade de páginas alterada")

        ids = [processo["processo_id"] for processo in item["processos"]]
        for indice, (pagina_original, pagina_modificada) in enumerate(
            zip(original.pages, modificado.pages),
            start=1,
        ):
            tamanho_original = (
                round(float(pagina_original.mediabox.width), 3),
                round(float(pagina_original.mediabox.height), 3),
            )
            tamanho_modificado = (
                round(float(pagina_modificada.mediabox.width), 3),
                round(float(pagina_modificada.mediabox.height), 3),
            )
            if tamanho_original != tamanho_modificado:
                raise ValueError(f"{nome}, página {indice}: tamanho alterado")

            texto = pagina_modificada.extract_text() or ""
            ausentes = [processo_id for processo_id in ids if processo_id not in texto]
            if ausentes:
                raise ValueError(
                    f"{nome}, página {indice}: IDs ausentes do PDF: {ausentes}"
                )
            total_marcacoes += len(ids)

        total_paginas += len(modificado.pages)
        resultado.append(
            {
                "pdf": nome,
                "paginas": len(modificado.pages),
                "ids": ids,
                "tamanho_bytes": (pasta_resultados / nome).stat().st_size,
            }
        )

    resumo = {
        "pdfs": len(resultado),
        "paginas": total_paginas,
        "marcacoes_de_qr_nas_paginas": total_marcacoes,
        "erros": 0,
        "arquivos": resultado,
    }
    saida_path.write_text(
        json.dumps(resumo, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({key: resumo[key] for key in ("pdfs", "paginas", "marcacoes_de_qr_nas_paginas", "erros")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

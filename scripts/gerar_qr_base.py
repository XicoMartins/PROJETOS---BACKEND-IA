"""Gera os QR Codes de todas as planilhas de processo de uma pasta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import qrcode

try:
    from scripts.gerar_qr_processos import (
        carregar_processos,
        montar_conteudo_qr,
        nome_seguro,
    )
except ModuleNotFoundError:
    from gerar_qr_processos import carregar_processos, montar_conteudo_qr, nome_seguro


def carregar_base(diretorio: Path | list[Path]) -> list[dict]:
    diretorios = [diretorio] if isinstance(diretorio, Path) else diretorio
    arquivos: list[Path] = []
    for pasta in diretorios:
        if not pasta.is_dir():
            raise FileNotFoundError(f"Pasta de planilhas não encontrada: {pasta}")
        arquivos.extend(
            arquivo
            for arquivo in pasta.glob("*.xlsx")
            if not arquivo.name.startswith("~$")
        )
    arquivos.sort(key=lambda arquivo: (arquivo.parent.name, arquivo.name))
    if not arquivos:
        raise ValueError("Nenhuma planilha .xlsx foi encontrada")

    registros: list[dict] = []
    ids_encontrados: dict[str, str] = {}
    for arquivo in arquivos:
        for processo in carregar_processos(arquivo):
            processo_id = processo["processo_id"]
            origem = f"{arquivo.name}, linha {processo['linha']}"
            if processo_id in ids_encontrados:
                raise ValueError(
                    f"PROCESSO_ID duplicado {processo_id}: "
                    f"{ids_encontrados[processo_id]} e {origem}"
                )
            ids_encontrados[processo_id] = origem
            registros.append({**processo, "planilha": arquivo.name})

    registros.sort(key=lambda registro: int(registro["processo_id"]))
    return registros


def gerar_qrs_da_base(
    diretorio: Path | list[Path],
    pasta_saida: Path,
    modo: str = "id",
    url_base: str | None = None,
) -> list[dict]:
    registros = carregar_base(diretorio)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    manifesto: list[dict] = []

    for registro in registros:
        conteudo = montar_conteudo_qr(
            registro["processo_id"],
            modo=modo,
            url_base=url_base,
        )
        nome_arquivo = (
            f"{registro['processo_id']}_{nome_seguro(registro['processo'])}.png"
        )
        nome_pasta = Path(registro["planilha"]).stem
        pasta_planilha = pasta_saida / nome_pasta
        pasta_planilha.mkdir(parents=True, exist_ok=True)
        caminho_qr = pasta_planilha / nome_arquivo
        caminho_relativo = caminho_qr.relative_to(pasta_saida)

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(conteudo)
        qr.make(fit=True)
        qr.make_image(fill_color="black", back_color="white").save(caminho_qr)

        manifesto.append(
            {
                **registro,
                "conteudo_qr": conteudo,
                "pasta_qr": nome_pasta,
                "arquivo_qr": caminho_relativo.as_posix(),
            }
        )

    (pasta_saida / "manifesto_qr.json").write_text(
        json.dumps(manifesto, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifesto


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera um QR Code para cada processo de todas as planilhas da base."
    )
    parser.add_argument(
        "--diretorio",
        required=True,
        action="append",
        type=Path,
        help="Pasta de planilhas; pode ser informada mais de uma vez",
    )
    parser.add_argument("--saida", required=True, type=Path)
    parser.add_argument("--modo", choices=("id", "url"), default="id")
    parser.add_argument("--url-base")
    return parser


def main() -> int:
    argumentos = construir_parser().parse_args()
    try:
        manifesto = gerar_qrs_da_base(
            diretorio=[pasta.resolve() for pasta in argumentos.diretorio],
            pasta_saida=argumentos.saida.resolve(),
            modo=argumentos.modo,
            url_base=argumentos.url_base,
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1

    print(f"{len(manifesto)} QR Codes gerados em: {argumentos.saida.resolve()}")
    print(f"Primeiro ID: {manifesto[0]['processo_id']}")
    print(f"Último ID: {manifesto[-1]['processo_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

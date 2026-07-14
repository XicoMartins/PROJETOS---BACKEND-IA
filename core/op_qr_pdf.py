"""Associação de Ordens de Produção a QR Codes e aplicação nos PDFs."""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import tempfile
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Callable

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


@dataclass(frozen=True)
class RegistroQr:
    processo_id: str
    cliente: str
    acabado: str
    ferramental: str
    processo: str
    arquivo_qr: str


@dataclass
class DadosOp:
    arquivo: Path
    paginas: int
    produto: str
    operacao: str
    marcados: list[str]
    ids_existentes: list[str] = field(default_factory=list)


@dataclass
class AssociacaoOp:
    dados: DadosOp
    registros: list[RegistroQr]
    status: str
    mensagem: str
    candidatos: list[RegistroQr] = field(default_factory=list)


_CACHE_MANIFESTO: dict[tuple[str, int, int], list[RegistroQr]] = {}


class ProcessamentoCancelado(Exception):
    """Interrupção solicitada pelo usuário sem caracterizar falha do processamento."""


def _verificar_cancelamento(cancelar: Callable[[], bool] | None) -> None:
    if cancelar and cancelar():
        raise ProcessamentoCancelado("Processamento cancelado pelo usuário.")


def normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").upper()
    texto = re.sub(r"[^A-Z0-9]+", " ", texto)
    return " ".join(texto.split())


def _normalizar_com_hifen(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = texto.encode("ascii", "ignore").decode("ascii").upper()
    texto = re.sub(r"[^A-Z0-9-]+", " ", texto)
    return " ".join(texto.split())


def _produto_sem_codigo(valor: str) -> str:
    return re.sub(r"\s+\d+\s*$", "", valor).strip()


def localizar_raiz_qr(caminho: Path) -> Path:
    """Localiza o manifesto na pasta escolhida ou em uma de suas pastas-pai."""
    atual = caminho
    for _ in range(6):
        if (atual / "manifesto_qr.json").is_file():
            return atual
        if atual.parent == atual:
            break
        atual = atual.parent
    raise FileNotFoundError(
        "manifesto_qr.json não encontrado. Selecione a pasta base_completa "
        "ou uma de suas subpastas."
    )


def carregar_manifesto(raiz_qr: Path) -> list[RegistroQr]:
    raiz_qr = localizar_raiz_qr(raiz_qr)
    manifesto = raiz_qr / "manifesto_qr.json"
    if not manifesto.is_file():
        raise FileNotFoundError(
            f"manifesto_qr.json não encontrado na pasta de QR Codes: {raiz_qr}"
        )
    estado = manifesto.stat()
    chave_cache = (str(manifesto), estado.st_mtime_ns, estado.st_size)
    armazenado = _CACHE_MANIFESTO.get(chave_cache)
    if armazenado is not None:
        return armazenado
    dados = json.loads(manifesto.read_text(encoding="utf-8"))
    if not isinstance(dados, list):
        raise ValueError("manifesto_qr.json inválido")

    registros: list[RegistroQr] = []
    ids: set[str] = set()
    for indice, item in enumerate(dados, start=1):
        processo_id = str(item.get("processo_id") or "").strip().zfill(6)
        if not re.fullmatch(r"\d{6}", processo_id):
            raise ValueError(f"Registro {indice}: PROCESSO_ID inválido")
        if processo_id in ids:
            raise ValueError(f"PROCESSO_ID duplicado no manifesto: {processo_id}")
        registro = RegistroQr(
            processo_id=processo_id,
            cliente=str(item.get("cliente") or "").strip(),
            acabado=str(item.get("acabado") or "").strip(),
            ferramental=str(item.get("ferramental") or "").strip(),
            processo=str(item.get("processo") or "").strip(),
            arquivo_qr=str(item.get("arquivo_qr") or "").strip(),
        )
        if not registro.processo or not registro.acabado or not registro.arquivo_qr:
            raise ValueError(f"Registro incompleto no manifesto: {processo_id}")
        ids.add(processo_id)
        registros.append(registro)
    _CACHE_MANIFESTO.clear()
    _CACHE_MANIFESTO[chave_cache] = registros
    return registros


def validar_qrs_associados(
    associacoes: list[AssociacaoOp], raiz_qr: Path
) -> None:
    """Valida somente os PNGs que realmente serão inseridos nos PDFs."""
    ausentes: list[str] = []
    vistos: set[str] = set()
    for associacao in associacoes:
        for registro in associacao.registros:
            if registro.processo_id in vistos:
                continue
            vistos.add(registro.processo_id)
            caminho = raiz_qr / registro.arquivo_qr
            if not caminho.is_file():
                ausentes.append(f"{registro.processo_id}: {caminho}")
    if ausentes:
        detalhes = "\n".join(ausentes[:20])
        complemento = "\n..." if len(ausentes) > 20 else ""
        raise FileNotFoundError(
            f"{len(ausentes)} QR Code(s) associado(s) não foram encontrados:\n"
            f"{detalhes}{complemento}"
        )


def extrair_dados_op(caminho: Path) -> DadosOp:
    try:
        with pdfplumber.open(caminho) as pdf:
            textos = [pagina.extract_text() or "" for pagina in pdf.pages]
    except Exception as exc:
        raise ValueError(f"{caminho.name}: não foi possível ler o PDF: {exc}") from exc

    texto = "\n".join(textos)
    linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
    linhas_norm = [normalizar(linha) for linha in linhas]

    produto = ""
    operacao = ""
    for indice, linha in enumerate(linhas_norm):
        if "DESCRICAO DO PRODUTO" in linha and indice + 1 < len(linhas):
            produto = _produto_sem_codigo(linhas[indice + 1])
        if linha.startswith("ORDEM DE PRODUCAO") and ":" in linhas[indice]:
            if indice + 1 < len(linhas):
                operacao = linhas[indice + 1]
    if not produto:
        raise ValueError(f"{caminho.name}: descrição do produto não localizada")
    if not operacao:
        raise ValueError(f"{caminho.name}: operação não localizada")

    marcados = [
        linha
        for linha in linhas
        if re.search(r"\(\s*[Xx]\s*\)", linha)
    ]
    ids = sorted(set(re.findall(r"(?<!\d)\d{6}(?!\d)", texto)))
    return DadosOp(
        arquivo=caminho,
        paginas=len(textos),
        produto=produto,
        operacao=operacao,
        marcados=marcados,
        ids_existentes=ids,
    )


def _similaridade(a: str, b: str) -> float:
    na, nb = normalizar(a), normalizar(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    sequencia = SequenceMatcher(None, na, nb).ratio()
    return 0.55 * sequencia + 0.45 * jaccard


def _filtrar_produto(dados: DadosOp, registros: list[RegistroQr]) -> list[RegistroQr]:
    produto = normalizar(dados.produto)
    exatos = [item for item in registros if normalizar(item.acabado) == produto]
    if exatos:
        return exatos
    notas = [(_similaridade(produto, item.acabado), item) for item in registros]
    melhor = max((nota for nota, _ in notas), default=0)
    return [item for nota, item in notas if nota == melhor and nota >= 0.88]


def _associar_intervalo(
    operacao: str,
    candidatos: list[RegistroQr],
) -> list[RegistroQr] | None:
    texto = _normalizar_com_hifen(operacao)
    padrao = re.compile(
        r"^(?P<prefixo>.*?)\bNEST\s*(?P<inicio>\d+)\s*-\s*"
        r"(?:NEST\s*)?(?P<fim>\d+)(?P<sufixo>.*)$"
    )
    achado = padrao.match(texto)
    if not achado:
        return None
    inicio, fim = int(achado["inicio"]), int(achado["fim"])
    if fim < inicio or fim - inicio > 100:
        return []
    prefixo = normalizar(achado["prefixo"])
    sufixo = normalizar(achado["sufixo"])
    resultado = []
    for numero in range(inicio, fim + 1):
        esperado = " ".join(
            parte for parte in (prefixo, "NEST", str(numero), sufixo) if parte
        )
        correspondencias = [
            item for item in candidatos if normalizar(item.processo) == esperado
        ]
        if len(correspondencias) != 1:
            return []
        resultado.extend(correspondencias)
    return resultado


def _pista_ferramental(dados: DadosOp) -> list[str]:
    marcado = normalizar(" ".join(dados.marcados))
    regras = (
        ("SOLDA MIG", ["SOLDA MIG"]),
        ("SOLDA PONTO", ["SOLDA PONTO"]),
        ("DOBRA CHAPA", ["DOBRADEIRA DE CHAPAS", "DOBRA CHAPA"]),
        ("DOBRA CORTE ARAME", ["DOBRADEIRA DE ARAMES", "DOBRA ARAME"]),
        ("GUILHOTINA", ["GUILHOTINA"]),
        ("CORTE TUBO", ["SERRA", "CORTE TUBO"]),
        ("LASER", ["LASER"]),
        ("PINTURA", ["PINTURA"]),
    )
    pistas: list[str] = []
    for chave, valores in regras:
        if chave in marcado:
            pistas.extend(valores)
    return pistas


def _associar_pintura(
    dados: DadosOp,
    candidatos: list[RegistroQr],
) -> list[RegistroQr] | None:
    contexto = normalizar(dados.operacao + " " + " ".join(dados.marcados))
    movimento = ""
    if "ENVIO A PINTURA" in contexto or "ENVIO PINTURA" in contexto:
        movimento = "ENVIO"
    elif "RETORNO DA PINTURA" in contexto or "RETORNO PINTURA" in contexto:
        movimento = "RETORNO"
    if not movimento:
        return None

    operacao = normalizar(dados.operacao)
    componente = next(
        (item for item in ("CORPO", "TESTEIRA") if item in operacao.split()), ""
    )
    cores = (
        "VERMELHO",
        "AMARELO",
        "BORDO",
        "MARROM",
        "PRETO",
        "BRANCO",
        "AZUL",
        "VERDE",
        "CINZA",
    )
    cor = next((item for item in cores if item in operacao.split()), "")
    if not componente or not cor:
        return []
    resultado = []
    for item in candidatos:
        processo = set(normalizar(item.processo).split())
        if {componente, movimento, cor}.issubset(processo):
            resultado.append(item)
    return resultado


def associar_op(dados: DadosOp, registros: list[RegistroQr]) -> AssociacaoOp:
    if dados.ids_existentes:
        por_id = {item.processo_id: item for item in registros}
        encontrados = [por_id[item] for item in dados.ids_existentes if item in por_id]
        if len(encontrados) == len(dados.ids_existentes):
            return AssociacaoOp(
                dados,
                encontrados,
                "ok",
                "Associação identificada no PDF já processado",
            )

    candidatos = _filtrar_produto(dados, registros)
    if not candidatos:
        return AssociacaoOp(
            dados, [], "erro", "Produto não encontrado na base de QR Codes", []
        )

    intervalo = _associar_intervalo(dados.operacao, candidatos)
    if intervalo is not None:
        if intervalo:
            return AssociacaoOp(dados, intervalo, "ok", "Intervalo de processos localizado")
        return AssociacaoOp(
            dados,
            [],
            "revisar",
            "Nem todos os processos do intervalo foram localizados",
            candidatos,
        )

    pintura = _associar_pintura(dados, candidatos)
    if pintura is not None:
        if len(pintura) == 1:
            return AssociacaoOp(dados, pintura, "ok", "Processo de pintura localizado")
        return AssociacaoOp(
            dados,
            [],
            "revisar",
            "Processo de pintura ausente ou ambíguo",
            pintura or candidatos,
        )

    operacao_norm = normalizar(dados.operacao)
    exatos = [item for item in candidatos if normalizar(item.processo) == operacao_norm]
    if len(exatos) == 1:
        return AssociacaoOp(dados, exatos, "ok", "Processo localizado")

    universo = exatos or candidatos
    pistas = _pista_ferramental(dados)
    avaliados: list[tuple[float, RegistroQr]] = []
    for item in universo:
        nota = _similaridade(dados.operacao, item.processo)
        ferramenta = normalizar(item.ferramental)
        if pistas and any(normalizar(pista) in ferramenta for pista in pistas):
            nota += 0.18
        avaliados.append((nota, item))
    avaliados.sort(key=lambda item: (-item[0], int(item[1].processo_id)))
    if not avaliados:
        return AssociacaoOp(dados, [], "erro", "Nenhum processo candidato", [])

    melhor = avaliados[0][0]
    margem = melhor - (avaliados[1][0] if len(avaliados) > 1 else 0)
    if melhor >= 0.82 and (margem >= 0.08 or len(avaliados) == 1):
        return AssociacaoOp(dados, [avaliados[0][1]], "ok", "Processo localizado")
    sugeridos = [item for nota, item in avaliados[:20] if nota >= max(0.45, melhor - 0.20)]
    return AssociacaoOp(
        dados,
        [],
        "revisar",
        "Associação ambígua; selecione o processo correto",
        sugeridos or [item for _, item in avaliados[:20]],
    )


def analisar_pasta(
    pasta_ops: Path,
    raiz_qr: Path,
    progresso: Callable[[int, int, str], None] | None = None,
    cancelar: Callable[[], bool] | None = None,
) -> list[AssociacaoOp]:
    _verificar_cancelamento(cancelar)
    if not pasta_ops.is_dir():
        raise FileNotFoundError(f"Pasta de OPs não encontrada: {pasta_ops}")
    pdfs = sorted(
        (item for item in pasta_ops.glob("*.pdf") if item.is_file()),
        key=lambda item: item.name.casefold(),
    )
    if not pdfs:
        raise ValueError("Nenhum PDF foi encontrado na pasta de OPs")
    registros = carregar_manifesto(raiz_qr)
    dados: list[DadosOp | None] = [None] * len(pdfs)
    trabalhadores = min(4, len(pdfs))
    with ThreadPoolExecutor(max_workers=trabalhadores) as executor:
        futuros = {
            executor.submit(extrair_dados_op, pdf): indice
            for indice, pdf in enumerate(pdfs)
        }
        concluidos = 0
        for futuro in as_completed(futuros):
            _verificar_cancelamento(cancelar)
            indice = futuros[futuro]
            dados[indice] = futuro.result()
            concluidos += 1
            if progresso:
                progresso(concluidos, len(pdfs), pdfs[indice].name)
    return [associar_op(item, registros) for item in dados if item is not None]


def _colunas_para(quantidade: int) -> int:
    if quantidade == 1:
        return 1
    if quantidade == 2:
        return 2
    if quantidade <= 6:
        return 3
    return 4


def _texto_curto(texto: str, limite: int = 28) -> str:
    texto = " ".join(texto.strip().split())
    return texto if len(texto) <= limite else texto[: limite - 3].rstrip() + "..."


@lru_cache(maxsize=256)
def _criar_sobreposicao_bytes(
    largura: float,
    altura: float,
    registros: tuple[RegistroQr, ...],
    raiz_qr_texto: str,
) -> bytes:
    raiz_qr = Path(raiz_qr_texto)
    memoria = io.BytesIO()
    desenho = canvas.Canvas(memoria, pagesize=(largura, altura))
    x0, x1 = largura * 0.708, largura * 0.966
    y0, y1 = altura * 0.644, altura * 0.804
    margem = min(largura, altura) * 0.004
    x0, x1, y0, y1 = x0 + margem, x1 - margem, y0 + margem, y1 - margem
    desenho.setFillColorRGB(1, 1, 1)
    desenho.rect(x0, y0, x1 - x0, y1 - y0, fill=1, stroke=0)

    quantidade = len(registros)
    colunas = _colunas_para(quantidade)
    linhas = math.ceil(quantidade / colunas)
    largura_celula = (x1 - x0) / colunas
    altura_celula = (y1 - y0) / linhas
    altura_rotulo = 16 if quantidade == 1 else 8
    tamanho_qr = min(
        largura_celula - 6,
        altura_celula - altura_rotulo - 5,
        94 if quantidade == 1 else 70,
    )
    if tamanho_qr < 18:
        raise ValueError("Muitos QR Codes para a área Imagem do Produto")

    for indice, registro in enumerate(registros):
        linha, coluna = divmod(indice, colunas)
        centro_x = x0 + coluna * largura_celula + largura_celula / 2
        topo = y1 - linha * altura_celula
        qr_x = centro_x - tamanho_qr / 2
        qr_y = topo - tamanho_qr - 3
        desenho.drawImage(
            ImageReader(raiz_qr / registro.arquivo_qr),
            qr_x,
            qr_y,
            width=tamanho_qr,
            height=tamanho_qr,
            preserveAspectRatio=True,
        )
        desenho.setFillColorRGB(0, 0, 0)
        fonte_id = 8 if quantidade == 1 else 5.5
        desenho.setFont("Helvetica-Bold", fonte_id)
        desenho.drawCentredString(
            centro_x, qr_y - fonte_id - 1, registro.processo_id
        )
        if quantidade == 1:
            desenho.setFont("Helvetica", 5.8)
            desenho.drawCentredString(
                centro_x,
                qr_y - fonte_id - 8,
                _texto_curto(registro.processo),
            )
    desenho.save()
    return memoria.getvalue()


def _criar_sobreposicao(
    largura: float,
    altura: float,
    registros: list[RegistroQr],
    raiz_qr: Path,
) -> PdfReader:
    conteudo = _criar_sobreposicao_bytes(
        largura,
        altura,
        tuple(registros),
        str(raiz_qr),
    )
    return PdfReader(io.BytesIO(conteudo))


def aplicar_qrs_pdf(
    origem: Path,
    destino: Path,
    registros: list[RegistroQr],
    raiz_qr: Path,
    cancelar: Callable[[], bool] | None = None,
) -> int:
    _verificar_cancelamento(cancelar)
    if not registros:
        raise ValueError(f"{origem.name}: nenhum QR Code associado")
    escritor = PdfWriter(clone_from=origem)
    for pagina_original in escritor.pages:
        _verificar_cancelamento(cancelar)
        if pagina_original.rotation:
            pagina_original.transfer_rotation_to_content()
        largura = float(pagina_original.mediabox.width)
        altura = float(pagina_original.mediabox.height)
        overlay = _criar_sobreposicao(largura, altura, registros, raiz_qr)
        pagina_original.merge_page(overlay.pages[0], over=True)

    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.tmp")
    with temporario.open("wb") as arquivo:
        escritor.write(arquivo)
    os.replace(temporario, destino)
    return len(escritor.pages)


def validar_pdf_resultado(
    original: Path,
    resultado: Path,
    registros: list[RegistroQr],
    cancelar: Callable[[], bool] | None = None,
) -> None:
    _verificar_cancelamento(cancelar)
    leitor_original = PdfReader(original)
    leitor_resultado = PdfReader(resultado)
    if len(leitor_original.pages) != len(leitor_resultado.pages):
        raise ValueError(f"{original.name}: quantidade de páginas foi alterada")
    ids = [item.processo_id for item in registros]
    for numero, (pagina_original, pagina_resultado) in enumerate(
        zip(leitor_original.pages, leitor_resultado.pages), start=1
    ):
        _verificar_cancelamento(cancelar)
        tamanho_original = tuple(round(float(valor), 3) for valor in pagina_original.mediabox)
        tamanho_resultado = tuple(round(float(valor), 3) for valor in pagina_resultado.mediabox)
        if tamanho_original != tamanho_resultado:
            raise ValueError(f"{original.name}, página {numero}: tamanho foi alterado")
        texto = pagina_resultado.extract_text() or ""
        ausentes = [processo_id for processo_id in ids if processo_id not in texto]
        if ausentes:
            raise ValueError(
                f"{original.name}, página {numero}: IDs ausentes no resultado: {ausentes}"
            )


def _executar_fase_paralela(
    associacoes: list[AssociacaoOp],
    tarefa: Callable[[AssociacaoOp], object],
    fase: str,
    progresso: Callable[[str, int, int, str], None] | None,
    cancelar: Callable[[], bool] | None,
) -> list[object]:
    resultados: list[object | None] = [None] * len(associacoes)
    trabalhadores = min(4, len(associacoes))
    with ThreadPoolExecutor(max_workers=trabalhadores) as executor:
        futuros = {
            executor.submit(tarefa, item): indice
            for indice, item in enumerate(associacoes)
        }
        concluidos = 0
        try:
            for futuro in as_completed(futuros):
                _verificar_cancelamento(cancelar)
                indice = futuros[futuro]
                resultados[indice] = futuro.result()
                concluidos += 1
                if progresso:
                    progresso(
                        fase,
                        concluidos,
                        len(associacoes),
                        associacoes[indice].dados.arquivo.name,
                    )
        except Exception:
            for futuro in futuros:
                futuro.cancel()
            raise
    return [item for item in resultados if item is not None]


def _copiar_atomico(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_name(f".{destino.name}.mtech.tmp")
    try:
        shutil.copy2(origem, temporario)
        os.replace(temporario, destino)
    finally:
        temporario.unlink(missing_ok=True)


def processar_associacoes(
    associacoes: list[AssociacaoOp],
    raiz_qr: Path,
    pasta_saida: Path | None = None,
    substituir_originais: bool = False,
    permitir_reprocessar: bool = False,
    progresso: Callable[[str, int, int, str], None] | None = None,
    cancelar: Callable[[], bool] | None = None,
) -> tuple[Path, dict]:
    _verificar_cancelamento(cancelar)
    if not associacoes:
        raise ValueError("Nenhuma OP foi informada para processamento")
    raiz_qr = localizar_raiz_qr(raiz_qr)
    pendentes = [item for item in associacoes if item.status not in {"ok", "manual"}]
    if pendentes:
        raise ValueError(
            f"Existem {len(pendentes)} PDFs sem associação confirmada"
        )
    ja_processados = [item for item in associacoes if item.dados.ids_existentes]
    if ja_processados and not permitir_reprocessar:
        raise ValueError(
            f"{len(ja_processados)} PDFs já possuem IDs de QR; habilite o reprocessamento"
        )
    validar_qrs_associados(associacoes, raiz_qr)
    _verificar_cancelamento(cancelar)

    pasta_ops = associacoes[0].dados.arquivo.parent
    instante = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino_base = (
        pasta_ops
        if substituir_originais
        else pasta_saida or pasta_ops.parent / f"OPS_COM_QR_{instante}"
    )
    backup = (
        pasta_ops.parent / f"BACKUP_OPS_ANTES_QR_{instante}"
        if substituir_originais
        else None
    )

    with tempfile.TemporaryDirectory(prefix="mtech_op_qr_") as temporario:
        temporario_path = Path(temporario)

        def gerar(item: AssociacaoOp) -> int:
            return aplicar_qrs_pdf(
                item.dados.arquivo,
                temporario_path / item.dados.arquivo.name,
                item.registros,
                raiz_qr,
                cancelar,
            )

        paginas = _executar_fase_paralela(
            associacoes, gerar, "gerando", progresso, cancelar
        )

        def validar(item: AssociacaoOp) -> bool:
            validar_pdf_resultado(
                item.dados.arquivo,
                temporario_path / item.dados.arquivo.name,
                item.registros,
                cancelar,
            )
            return True

        _executar_fase_paralela(
            associacoes, validar, "validando", progresso, cancelar
        )
        _verificar_cancelamento(cancelar)

        if not substituir_originais:
            if destino_base.exists() and any(
                (destino_base / item.dados.arquivo.name).exists()
                for item in associacoes
            ):
                raise FileExistsError(
                    f"A pasta de saída já contém PDFs com os mesmos nomes: {destino_base}"
                )
            destino_base.mkdir(parents=True, exist_ok=True)

        copiados: list[Path] = []
        backup_criado = False
        try:
            if backup:
                backup.mkdir(parents=True, exist_ok=False)
                backup_criado = True
                for indice, item in enumerate(associacoes, start=1):
                    _verificar_cancelamento(cancelar)
                    _copiar_atomico(
                        item.dados.arquivo, backup / item.dados.arquivo.name
                    )
                    if progresso:
                        progresso(
                            "backup",
                            indice,
                            len(associacoes),
                            item.dados.arquivo.name,
                        )

            for indice, item in enumerate(associacoes, start=1):
                _verificar_cancelamento(cancelar)
                destino = destino_base / item.dados.arquivo.name
                _copiar_atomico(
                    temporario_path / item.dados.arquivo.name, destino
                )
                copiados.append(destino)
                if progresso:
                    progresso(
                        "salvando",
                        indice,
                        len(associacoes),
                        item.dados.arquivo.name,
                    )
        except Exception:
            if backup_criado and backup and copiados:
                for destino in copiados:
                    _copiar_atomico(backup / destino.name, destino)
            elif backup_criado and backup:
                shutil.rmtree(backup, ignore_errors=True)
            else:
                for destino in copiados:
                    destino.unlink(missing_ok=True)
                if destino_base.exists() and not any(destino_base.iterdir()):
                    destino_base.rmdir()
            raise

    relatorio_itens = [
        {
            "pdf": item.dados.arquivo.name,
            "produto": item.dados.produto,
            "operacao": item.dados.operacao,
            "paginas": paginas[indice],
            "processos": [asdict(registro) for registro in item.registros],
        }
        for indice, item in enumerate(associacoes)
    ]
    relatorio = {
        "data_hora": datetime.now().isoformat(timespec="seconds"),
        "pasta_ops": str(pasta_ops),
        "pasta_qrs": str(raiz_qr),
        "pasta_resultado": str(destino_base),
        "backup": str(backup) if backup else None,
        "pdfs": len(relatorio_itens),
        "associacoes_qr": sum(len(item["processos"]) for item in relatorio_itens),
        "arquivos": relatorio_itens,
    }
    relatorio_path = destino_base / "RELATORIO_QR_OPS.json"
    relatorio_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return destino_base, relatorio

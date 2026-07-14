"""Normalização e leitura dos identificadores usados nos QR Codes."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit


PROCESSO_ID_PATTERN = re.compile(r"^\d{6}$")


def normalize_process_id(value: object) -> str:
    """Retorna um PROCESSO_ID com seis dígitos ou levanta ValueError."""
    if value is None or isinstance(value, bool):
        raise ValueError("ID do processo vazio ou inválido.")

    if isinstance(value, int):
        text = str(value)
    elif isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value).strip()

    if text.isdigit() and len(text) <= 6:
        text = text.zfill(6)

    if not PROCESSO_ID_PATTERN.fullmatch(text):
        raise ValueError("O ID do processo deve conter exatamente 6 dígitos.")
    return text


def extract_process_id(value: object) -> str:
    """Aceita somente o ID ou uma URL com o parâmetro processo_id."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("Leia o QR Code ou informe o ID do processo.")

    if text.isdigit():
        return normalize_process_id(text)

    parts = urlsplit(text)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("QR inválido. Informe um ID ou uma URL HTTP/HTTPS válida.")

    values = parse_qs(parts.query, keep_blank_values=True).get("processo_id", [])
    if len(values) != 1 or not values[0].strip():
        raise ValueError("A URL do QR deve possuir um único parâmetro processo_id.")
    return normalize_process_id(values[0])

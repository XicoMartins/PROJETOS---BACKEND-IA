"""Componente de câmera que decodifica QR Codes no navegador do usuário."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import streamlit as st


COMPONENT_DIR = Path(__file__).resolve().parents[1] / "components" / "qr_scanner"


@lru_cache(maxsize=1)
def _component_renderer():
    html = (COMPONENT_DIR / "scanner.html").read_text(encoding="utf-8")
    css = (COMPONENT_DIR / "scanner.css").read_text(encoding="utf-8")
    javascript = (COMPONENT_DIR / "dist" / "scanner.js").read_text(
        encoding="utf-8"
    )
    return st.components.v2.component(
        "mtech_qr_browser_scanner",
        html=html,
        css=css,
        js=javascript,
    )


def extract_scanned_value(result: Any) -> str | None:
    """Extrai o último texto lido de um resultado do componente Streamlit."""
    if result is None:
        return None
    payload = getattr(result, "scanned", None)
    if payload is None and isinstance(result, Mapping):
        payload = result.get("scanned")
    if isinstance(payload, list):
        payload = payload[-1] if payload else None
    if isinstance(payload, Mapping):
        payload = payload.get("value")
    value = str(payload or "").strip()
    return value or None


def qr_browser_scanner(*, key: str) -> str | None:
    """Monta o leitor local e retorna o ID/URL somente após uma leitura."""
    result = _component_renderer()(key=key)
    return extract_scanned_value(result)

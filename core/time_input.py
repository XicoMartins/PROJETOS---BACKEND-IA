"""Campo HHMM controlado no navegador para evitar perda do valor no celular."""

from __future__ import annotations

from functools import lru_cache
import hashlib
from pathlib import Path
from typing import Any, Mapping

import streamlit as st


COMPONENT_DIR = Path(__file__).resolve().parents[1] / "components" / "time_input"


@lru_cache(maxsize=1)
def _component_renderer():
    return st.components.v2.component(
        "mtech_time_hhmm_input",
        html=(COMPONENT_DIR / "time_input.html").read_text(encoding="utf-8"),
        css=(COMPONENT_DIR / "time_input.css").read_text(encoding="utf-8"),
        js=(COMPONENT_DIR / "time_input.js").read_text(encoding="utf-8"),
    )


def extract_changed_value(result: Any) -> str | None:
    payload = getattr(result, "changed", None)
    if payload is None and isinstance(result, Mapping):
        payload = result.get("changed")
    if isinstance(payload, list):
        payload = payload[-1] if payload else None
    if isinstance(payload, Mapping):
        payload = payload.get("value")
    if payload is None:
        return None
    return str(payload).strip()


def safe_component_key(key: str) -> str:
    """Cria uma chave estável sem o separador ``__`` reservado pelo Streamlit."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return f"hhmm-{digest}"


def time_hhmm_component(*, label: str, value: str, key: str) -> str:
    """Renderiza o campo e mantém a última confirmação na sessão."""
    value_key = f"{key}__confirmed_value"
    current = str(st.session_state.get(value_key, value))
    result = _component_renderer()(
        key=safe_component_key(key),
        data={"label": label, "value": current, "key": key},
        on_changed_change=lambda: None,
    )
    changed = extract_changed_value(result)
    if changed is not None and changed != current:
        st.session_state[value_key] = changed
        return changed
    return current

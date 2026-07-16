"""Conversão dos horários digitados no formato numérico HHMM."""

from __future__ import annotations

from datetime import time


def time_to_hhmm(value: time | None) -> int:
    """Converte um horário para o número usado pelo campo HHMM."""
    if not isinstance(value, time):
        return 0
    return value.hour * 100 + value.minute


def parse_hhmm(value: int | str | None) -> time | None:
    """Converte até quatro dígitos HHMM em horário, rejeitando minutos inválidos."""
    text = str(value if value is not None else "").strip()
    if not text.isdigit() or len(text) > 4:
        return None

    number = int(text)
    hour, minute = divmod(number, 100)
    if hour > 23 or minute > 59:
        return None
    return time(hour, minute)

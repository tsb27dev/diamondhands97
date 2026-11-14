"""Descodificação de DTCs OBD-II (Mode 03/07/0A)."""
from __future__ import annotations

_SYSTEM = "PCBU"


def decode_dtc(b1: int, b2: int) -> str:
    return f"{_SYSTEM[b1 >> 6]}{(b1 >> 4) & 3}{b1 & 0xF:X}{b2 >> 4:X}{b2 & 0xF:X}"


def decode_dtcs(payload: bytes, has_count: bool) -> list[str]:
    """payload = resposta completa (43 [n] pares...). Ignora pares 0000 (padding)."""
    body = payload[2:] if has_count else payload[1:]
    return [decode_dtc(body[i], body[i + 1]) for i in range(0, len(body) - 1, 2) if body[i] or body[i + 1]]

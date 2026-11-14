"""OBD-II (ISO 15765-4) sobre CAN: pedidos Mode 01 e descodificação de PIDs.

Útil como *verdade de referência* para correlacionar com mensagens proprietárias
(RPM, velocidade, temperatura do líquido de refrigeração, ...).
"""
from __future__ import annotations

import time

REQ_ID = 0x7DF           # broadcast funcional
RESP_RANGE = range(0x7E8, 0x7F0)

# pid -> (nome, unidade, função(bytes_de_dados) -> valor)
PIDS = {
    0x04: ("engine_load", "%", lambda d: d[0] * 100 / 255),
    0x05: ("coolant_temp", "°C", lambda d: d[0] - 40),
    0x0B: ("map", "kPa", lambda d: d[0]),
    0x0C: ("rpm", "rpm", lambda d: (d[0] * 256 + d[1]) / 4),
    0x0D: ("speed", "km/h", lambda d: d[0]),
    0x0F: ("intake_temp", "°C", lambda d: d[0] - 40),
    0x10: ("maf", "g/s", lambda d: (d[0] * 256 + d[1]) / 100),
    0x11: ("throttle", "%", lambda d: d[0] * 100 / 255),
    0x23: ("fuel_rail_pressure", "kPa", lambda d: (d[0] * 256 + d[1]) * 10),
    0x2F: ("fuel_level", "%", lambda d: d[0] * 100 / 255),
    0x5C: ("oil_temp", "°C", lambda d: d[0] - 40),
}


def build_request(pid: int, mode: int = 0x01) -> bytes:
    return bytes([2, mode, pid, 0, 0, 0, 0, 0])


def decode_response(data: bytes):
    """Single-frame Mode 01. Devolve (pid, nome, valor, unidade) ou None."""
    if len(data) < 4 or data[1] != 0x41:
        return None
    n, pid = data[0], data[2]
    payload = data[3 : 1 + n]
    if pid in PIDS:
        name, unit, fn = PIDS[pid]
        try:
            return pid, name, fn(payload), unit
        except IndexError:
            return None
    return pid, f"pid_{pid:02X}", payload.hex(), ""


def supported_pids(data: bytes) -> list[int]:
    """Descodifica resposta aos PIDs 00/20/40/... (bitmask de 4 bytes)."""
    base = data[2]
    mask = int.from_bytes(data[3:7], "big")
    return [base + i + 1 for i in range(32) if mask >> (31 - i) & 1]


def scan(channel: str = "can0", bustype: str = "socketcan", bitrate: int = 500000, seconds: float = 20.0):
    """Pergunta a ECU pelos PIDs suportados e imprime valores (requer python-can)."""
    import can  # noqa: WPS433

    bus = can.Bus(interface=bustype, channel=channel, bitrate=bitrate)
    try:
        bus.send(can.Message(arbitration_id=REQ_ID, data=build_request(0x00), is_extended_id=False))
        t0, found = time.time(), []
        while time.time() - t0 < 2:
            m = bus.recv(0.5)
            if m and m.arbitration_id in RESP_RANGE and m.data[1:3] == bytes([0x41, 0x00]):
                found = supported_pids(bytes(m.data))
                print(f"ECU 0x{m.arbitration_id:X} suporta: {[hex(p) for p in found]}")
                break
        if not found:
            print("Sem resposta OBD-II em CAN. Ver docs/01-hardware-e-bus.md (K-line?).")
            return
        t0 = time.time()
        while time.time() - t0 < seconds:
            for pid in (p for p in found if p in PIDS):
                bus.send(can.Message(arbitration_id=REQ_ID, data=build_request(pid), is_extended_id=False))
                m = bus.recv(0.2)
                if m and m.arbitration_id in RESP_RANGE:
                    r = decode_response(bytes(m.data))
                    if r:
                        print(f"{time.time():.3f} {r[1]:>20} = {r[2]:.1f} {r[3]}")
    finally:
        bus.shutdown()

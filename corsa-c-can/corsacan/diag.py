"""Diagnóstico próprio: ler/apagar DTCs, dados em tempo real, VIN.

Dois transportes com a mesma interface `request(payload) -> resposta`:
 * CanLink   - OBD-II sobre CAN (ISO 15765-4 / ISO-TP)   [python-can]
 * KLineLink - ISO 14230 (KWP2000) ou ISO 9141-2          [pyserial + cabo K-line]
"""
from __future__ import annotations

import time

from . import dtc, obd


class DiagError(Exception):
    pass


def check_negative(resp: bytes, service: int):
    if resp and resp[0] == 0x7F:
        raise DiagError(f"Resposta negativa ao serviço {service:02X}: código {resp[2]:02X}" if len(resp) > 2 else "NRC")


# ----------------------------------------------------------------- CAN / ISO-TP
class CanLink:
    has_count = True

    def __init__(self, bus, req_id=0x7DF, timeout=1.0):
        import can  # noqa: WPS433
        self._can, self.bus, self.req_id, self.timeout = can, bus, req_id, timeout

    @classmethod
    def open(cls, channel="can0", bustype="socketcan", bitrate=500000):
        import can
        return cls(can.Bus(interface=bustype, channel=channel, bitrate=bitrate))

    def _send(self, cid, data):
        self.bus.send(self._can.Message(arbitration_id=cid, data=bytes(data).ljust(8, b"\x00"), is_extended_id=False))

    def request(self, payload: bytes) -> bytes:
        if len(payload) > 7:
            raise ValueError("Só single-frame no pedido")
        self._send(self.req_id, bytes([len(payload)]) + payload)
        return self._receive()

    def _receive(self) -> bytes:
        deadline = time.time() + self.timeout
        buf, total, src = bytearray(), 0, None
        while time.time() < deadline:
            m = self.bus.recv(0.1)
            if m is None or not (0x7E8 <= m.arbitration_id <= 0x7EF):
                continue
            if src is not None and m.arbitration_id != src:
                continue
            d, pci = bytes(m.data), m.data[0] >> 4
            if pci == 0:                                   # single frame
                n = d[0] & 0xF
                out = d[1 : 1 + n]
                if len(out) >= 3 and out[0] == 0x7F and out[2] == 0x78:   # response pending
                    deadline = time.time() + 5
                    continue
                return out
            if pci == 1:                                   # first frame
                src, total = m.arbitration_id, ((d[0] & 0xF) << 8) | d[1]
                buf = bytearray(d[2:8])
                self._send(src - 8, b"\x30\x00\x00")       # flow control: continue
            elif pci == 2 and src is not None:             # consecutive frame
                buf += d[1:8]
                if len(buf) >= total:
                    return bytes(buf[:total])
        raise DiagError("Sem resposta (timeout)")


# ----------------------------------------------------------------- K-line
def kline_checksum(b: bytes) -> int:
    return sum(b) & 0xFF


def kwp_frame(data: bytes, target=0x33, source=0xF1) -> bytes:
    if len(data) > 63:
        raise ValueError("máx. 63 bytes")
    f = bytes([0xC0 | len(data), target, source]) + data  # 0xC0 = endereçamento funcional
    return f + bytes([kline_checksum(f)])


def iso9141_frame(data: bytes) -> bytes:
    f = bytes([0x68, 0x6A, 0xF1]) + data
    return f + bytes([kline_checksum(f)])


def split_kline(raw: bytes) -> list[bytes]:
    """Separa uma rajada de bytes em mensagens (devolve só os dados, sem cabeçalho/checksum)."""
    out, i = [], 0
    while i + 4 <= len(raw):
        if raw[i] & 0x80 and raw[i] & 0x3F:                 # KWP com comprimento no formato
            n = 4 + (raw[i] & 0x3F)
            if i + n <= len(raw) and kline_checksum(raw[i : i + n - 1]) == raw[i + n - 1]:
                out.append(raw[i + 3 : i + n - 1]); i += n; continue
        for n in range(5, 12):                              # ISO 9141: tamanho desconhecido
            if i + n <= len(raw) and raw[i] == 0x48 and kline_checksum(raw[i : i + n - 1]) == raw[i + n - 1]:
                out.append(raw[i + 3 : i + n - 1]); i += n; break
        else:
            i += 1
    return out


class KLineLink:
    """ATENÇÃO: não testado em hardware real. Requer cabo K-line (FTDI + circuito L9637/MC33290)."""
    has_count = False

    def __init__(self, port, init="fast", baud=10400):
        import serial  # pyserial
        self.s = serial.Serial(port, baud, timeout=0.3)
        self.init, self.framer = init, (kwp_frame if init == "fast" else iso9141_frame)
        self._init_bus()

    def _write(self, b: bytes):
        self.s.reset_input_buffer()
        for x in b:                       # K-line é half-duplex: lê o eco byte a byte
            self.s.write(bytes([x])); self.s.read(1); time.sleep(0.005)

    def _init_bus(self):
        s = self.s
        if self.init == "fast":           # ISO 14230 fast init: TiniL=25 ms, depois StartCommunication
            s.break_condition = True; time.sleep(0.025)
            s.break_condition = False; time.sleep(0.025)
            self._write(kwp_frame(b"\x81"))
            if not self._read():
                raise DiagError("Sem resposta ao StartCommunication (tenta --init slow)")
        else:                             # ISO 9141 5-baud init, endereço 0x33
            s.break_condition = False; time.sleep(0.3)
            for bit in [0] + [(0x33 >> i) & 1 for i in range(8)] + [1]:
                s.break_condition = (bit == 0); time.sleep(0.2)
            s.break_condition = False
            s.reset_input_buffer()
            sync = s.read(1)
            if sync != b"\x55":
                raise DiagError(f"Sem sync 0x55 (recebi {sync!r})")
            kb1, kb2 = s.read(1), s.read(1)
            if len(kb2) != 1:
                raise DiagError("Key bytes em falta")
            time.sleep(0.03); s.write(bytes([kb2[0] ^ 0xFF])); s.read(1)
            if s.read(1) != bytes([0x33 ^ 0xFF]):
                raise DiagError("ECU não confirmou o endereço")

    def _read(self) -> list[bytes]:
        raw = bytearray()
        while True:
            c = self.s.read(1)
            if not c:
                break
            raw += c
        return split_kline(bytes(raw))

    def request(self, payload: bytes) -> bytes:
        self._write(self.framer(payload))
        msgs = self._read()
        if not msgs:
            raise DiagError("Sem resposta (timeout)")
        return msgs[0]


# ----------------------------------------------------------------- operações
def read_dtcs(link, service=0x03) -> list[str]:
    r = link.request(bytes([service]))
    check_negative(r, service)
    if r[0] != service + 0x40:
        raise DiagError(f"Resposta inesperada: {r.hex()}")
    return dtc.decode_dtcs(r, link.has_count)


def clear_dtcs(link):
    r = link.request(b"\x04")
    check_negative(r, 4)
    if r[0] != 0x44:
        raise DiagError(f"Resposta inesperada: {r.hex()}")


def read_pid(link, pid: int):
    r = link.request(bytes([0x01, pid]))
    check_negative(r, 1)
    return obd.decode_payload(r)


def read_vin(link) -> str:
    r = link.request(b"\x09\x02")
    check_negative(r, 9)
    return bytes(c for c in r[3:] if 32 <= c < 127).decode()


def live(link, pids, seconds=30):
    t0 = time.time()
    while time.time() - t0 < seconds:
        row = []
        for pid in pids:
            try:
                r = read_pid(link, pid)
                row.append(f"{r[1]}={r[2]:.1f}{r[3]}" if r else f"pid{pid:02X}=?")
            except DiagError:
                row.append(f"pid{pid:02X}=n/d")
        print(" | ".join(row), flush=True)

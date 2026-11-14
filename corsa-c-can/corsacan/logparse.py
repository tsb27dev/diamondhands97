"""Leitura de logs CAN (candump -L, candump -l e CSV simples)."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Frame:
    ts: float
    iface: str
    can_id: int
    data: bytes

    @property
    def dlc(self) -> int:
        return len(self.data)


# (1700000000.123456) can0 123#DEADBEEF   (formato `candump -L`)
_LOG_RE = re.compile(r"^\((?P<ts>[\d.]+)\)\s+(?P<if>\S+)\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)")
# formato `candump -ta`:  (1700000000.123456)  can0  123   [8]  DE AD BE EF ...
_DUMP_RE = re.compile(
    r"^\((?P<ts>[\d.]+)\)\s+(?P<if>\S+)\s+(?P<id>[0-9A-Fa-f]+)\s+\[(?P<n>\d+)\]\s*(?P<data>(?:[0-9A-Fa-f]{2}\s*)*)"
)


def parse_line(line: str) -> Frame | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = _LOG_RE.match(line)
    if m:
        return Frame(float(m["ts"]), m["if"], int(m["id"], 16), bytes.fromhex(m["data"]))
    m = _DUMP_RE.match(line)
    if m:
        return Frame(float(m["ts"]), m["if"], int(m["id"], 16), bytes.fromhex(m["data"].replace(" ", "")))
    return None


def read_log(path: str) -> Iterator[Frame]:
    """Lê `candump -L` ou CSV (ts,id,data_hex). Linhas inválidas são ignoradas."""
    with open(path, newline="") as fh:
        if path.lower().endswith(".csv"):
            for row in csv.reader(fh):
                if len(row) < 3:
                    continue
                try:
                    yield Frame(float(row[0]), "csv", int(row[1], 16), bytes.fromhex(row[2]))
                except ValueError:
                    continue  # cabeçalho
        else:
            for line in fh:
                f = parse_line(line)
                if f:
                    yield f

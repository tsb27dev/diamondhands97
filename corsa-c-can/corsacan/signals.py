"""Definições de sinais (JSON) -> descodificação e exportação para .dbc.

Convenção de `start` igual à do DBC:
 - little endian (Intel, @1): start = bit menos significativo
 - big endian (Motorola, @0): start = bit mais significativo (numeração DBC)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .logparse import Frame


@dataclass
class Signal:
    name: str
    start: int
    length: int
    byte_order: str = "little"  # "little" | "big"
    signed: bool = False
    factor: float = 1.0
    offset: float = 0.0
    unit: str = ""

    def raw(self, data: bytes) -> int | None:
        if self.byte_order == "little":
            bits = [self.start + i for i in range(self.length)]
        else:
            bits, p = [], self.start
            for _ in range(self.length):
                bits.append(p)
                p = p + 15 if p % 8 == 0 else p - 1
            bits.reverse()  # LSB primeiro
        if max(bits) >= len(data) * 8:
            return None
        v = 0
        for i, p in enumerate(bits):
            v |= (data[p // 8] >> (p % 8) & 1) << i
        if self.signed and v >> (self.length - 1) & 1:
            v -= 1 << self.length
        return v

    def phys(self, data: bytes) -> float | None:
        r = self.raw(data)
        return None if r is None else r * self.factor + self.offset


@dataclass
class Message:
    can_id: int
    name: str
    dlc: int
    signals: list[Signal]

    def decode(self, data: bytes) -> dict[str, float | None]:
        return {s.name: s.phys(data) for s in self.signals}


def load_signals(path: str) -> dict[int, Message]:
    with open(path) as fh:
        doc = json.load(fh)
    msgs: dict[int, Message] = {}
    for m in doc["messages"]:
        cid = int(m["id"], 0)
        msgs[cid] = Message(cid, m["name"], m.get("dlc", 8), [Signal(**s) for s in m["signals"]])
    return msgs


def decode_frames(frames: Iterable[Frame], msgs: dict[int, Message]):
    for f in frames:
        m = msgs.get(f.can_id)
        if m:
            yield f.ts, m.name, m.decode(f.data)


def to_dbc(msgs: dict[int, Message]) -> str:
    out = ['VERSION ""', "", "NS_ :", "", "BS_:", "", "BU_: ECU", ""]
    for m in msgs.values():
        out.append(f"BO_ {m.can_id} {m.name}: {m.dlc} ECU")
        for s in m.signals:
            bo = 1 if s.byte_order == "little" else 0
            sg = "-" if s.signed else "+"
            out.append(
                f' SG_ {s.name} : {s.start}|{s.length}@{bo}{sg} ({s.factor:g},{s.offset:g}) [0|0] "{s.unit}" Vector__XXX'
            )
        out.append("")
    return "\n".join(out)

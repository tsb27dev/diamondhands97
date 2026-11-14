"""Estatísticas por ID, deteção de contadores/checksums e correlação com sinais conhecidos."""
from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

from .logparse import Frame


@dataclass
class IdStats:
    can_id: int
    count: int = 0
    period_ms: float = 0.0
    jitter_ms: float = 0.0
    dlcs: set[int] = field(default_factory=set)
    byte_unique: list[int] = field(default_factory=list)
    byte_min: list[int] = field(default_factory=list)
    byte_max: list[int] = field(default_factory=list)
    counter_bytes: list[int] = field(default_factory=list)
    constant_bytes: list[int] = field(default_factory=list)
    bit_toggles: list[int] = field(default_factory=list)  # 64 entradas


def group_by_id(frames: Iterable[Frame]) -> dict[int, list[Frame]]:
    out: dict[int, list[Frame]] = defaultdict(list)
    for f in frames:
        out[f.can_id].append(f)
    return out


def _is_counter(values: list[int]) -> bool:
    """Byte que incrementa +1 (módulo 16 ou 256) em >=90% das transições."""
    if len(values) < 8:
        return False
    for mod in (16, 256):
        ok = sum(1 for a, b in zip(values, values[1:]) if (b - a) % mod == 1)
        if ok / (len(values) - 1) >= 0.9:
            return True
    return False


def id_stats(can_id: int, frames: list[Frame]) -> IdStats:
    frames = sorted(frames, key=lambda f: f.ts)
    s = IdStats(can_id=can_id, count=len(frames))
    s.dlcs = {f.dlc for f in frames}
    if len(frames) > 1:
        dts = [(b.ts - a.ts) * 1000 for a, b in zip(frames, frames[1:])]
        s.period_ms = statistics.fmean(dts)
        s.jitter_ms = statistics.pstdev(dts)
    n = max(s.dlcs)
    s.bit_toggles = [0] * (n * 8)
    for i in range(n):
        col = [f.data[i] for f in frames if f.dlc > i]
        s.byte_unique.append(len(set(col)))
        s.byte_min.append(min(col))
        s.byte_max.append(max(col))
        if len(set(col)) == 1:
            s.constant_bytes.append(i)
        elif _is_counter(col):
            s.counter_bytes.append(i)
    for a, b in zip(frames, frames[1:]):
        for i in range(min(a.dlc, b.dlc)):
            x = a.data[i] ^ b.data[i]
            for bit in range(8):
                if x >> bit & 1:
                    s.bit_toggles[i * 8 + bit] += 1
    return s


def all_stats(frames: Iterable[Frame]) -> list[IdStats]:
    return [id_stats(i, fs) for i, fs in sorted(group_by_id(frames).items())]


# ---------- diff entre duas capturas (ex.: antes/depois de carregar num botão) ----------

def bit_states(frames: list[Frame]) -> dict[int, list[set[int]]]:
    """can_id -> lista (por bit) com os valores observados {0,1}."""
    out: dict[int, list[set[int]]] = {}
    for cid, fs in group_by_id(frames).items():
        n = max(f.dlc for f in fs)
        bits = [set() for _ in range(n * 8)]
        for f in fs:
            for i, byte in enumerate(f.data):
                for b in range(8):
                    bits[i * 8 + b].add(byte >> b & 1)
        out[cid] = bits
    return out


def diff_logs(a: list[Frame], b: list[Frame]):
    """Devolve (ids só em A, ids só em B, {id: [(byte, bit, estadoA, estadoB)]})
    para bits estáveis em ambas as capturas mas com valor diferente."""
    sa, sb = bit_states(a), bit_states(b)
    only_a = sorted(set(sa) - set(sb))
    only_b = sorted(set(sb) - set(sa))
    changed: dict[int, list[tuple[int, int, int, int]]] = {}
    for cid in set(sa) & set(sb):
        for idx, (x, y) in enumerate(zip(sa[cid], sb[cid])):
            if len(x) == 1 and len(y) == 1 and x != y:
                changed.setdefault(cid, []).append((idx // 8, idx % 8, next(iter(x)), next(iter(y))))
    return only_a, only_b, changed


# ---------- correlação com sinal de referência (ex.: RPM lido por OBD-II) ----------

def _pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return 0.0
    return statistics.correlation(x, y)


def _sample(ref: list[tuple[float, float]], ts: float) -> float | None:
    """Valor de referência mais próximo (busca binária)."""
    import bisect
    keys = [t for t, _ in ref]
    i = bisect.bisect_left(keys, ts)
    cands = [j for j in (i - 1, i) if 0 <= j < len(ref)]
    if not cands:
        return None
    j = min(cands, key=lambda k: abs(keys[k] - ts))
    return ref[j][1] if abs(keys[j] - ts) < 1.0 else None


def correlate(frames: list[Frame], ref: list[tuple[float, float]], top: int = 15):
    """Para cada ID, testa bytes isolados e pares (big/little endian) contra `ref`.
    Devolve lista ordenada de (|r|, can_id, descrição)."""
    ref = sorted(ref)
    results = []
    for cid, fs in group_by_id(frames).items():
        fs = sorted(fs, key=lambda f: f.ts)
        n = min(f.dlc for f in fs)
        pts = [(f, _sample(ref, f.ts)) for f in fs]
        pts = [(f, r) for f, r in pts if r is not None]
        if len(pts) < 10:
            continue
        ys = [r for _, r in pts]
        cands: dict[str, list[float]] = {}
        for i in range(n):
            cands[f"byte{i}"] = [f.data[i] for f, _ in pts]
        for i in range(n - 1):
            cands[f"u16_be[{i}:{i+2}]"] = [f.data[i] << 8 | f.data[i + 1] for f, _ in pts]
            cands[f"u16_le[{i}:{i+2}]"] = [f.data[i + 1] << 8 | f.data[i] for f, _ in pts]
        for name, xs in cands.items():
            r = _pearson(xs, ys)
            if abs(r) > 0.5:
                results.append((abs(r), r, cid, name))
    results.sort(reverse=True)
    return results[:top]

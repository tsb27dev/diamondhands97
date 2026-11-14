from __future__ import annotations

import argparse
import csv
import sys

from . import analyze, signals
from .logparse import read_log
from .obd import PIDS, decode_response


def _hexrow(vals):
    return " ".join(f"{v:02X}" for v in vals)


def cmd_stats(a):
    stats = analyze.all_stats(read_log(a.log))
    print(f"{'ID':>5} {'n':>7} {'per(ms)':>8} {'jit':>6} dlc  contadores  constantes  bytes variáveis (min-max)")
    for s in stats:
        var = [f"{i}:{s.byte_min[i]:02X}-{s.byte_max[i]:02X}" for i in range(len(s.byte_unique))
               if i not in s.constant_bytes and i not in s.counter_bytes]
        print(f"{s.can_id:03X}  {s.count:>7} {s.period_ms:8.1f} {s.jitter_ms:6.1f} {sorted(s.dlcs)}  "
              f"{s.counter_bytes}  {s.constant_bytes}  {' '.join(var)}")


def cmd_diff(a):
    fa, fb = list(read_log(a.a)), list(read_log(a.b))
    oa, ob, ch = analyze.diff_logs(fa, fb)
    if oa: print("IDs só em A:", " ".join(f"{i:03X}" for i in oa))
    if ob: print("IDs só em B:", " ".join(f"{i:03X}" for i in ob))
    for cid, bits in sorted(ch.items()):
        print(f"{cid:03X}: " + ", ".join(f"byte{b}.bit{k} {x}->{y}" for b, k, x, y in bits))
    if not (oa or ob or ch):
        print("Sem diferenças em bits estáveis.")


def cmd_correlate(a):
    ref = []
    with open(a.ref) as fh:
        for row in csv.reader(fh):
            try:
                ref.append((float(row[0]), float(row[1])))
            except (ValueError, IndexError):
                pass
    for absr, r, cid, name in analyze.correlate(list(read_log(a.log)), ref, a.top):
        print(f"{cid:03X}  {name:<16} r={r:+.3f}")


def cmd_decode(a):
    msgs = signals.load_signals(a.signals)
    for ts, name, vals in signals.decode_frames(read_log(a.log), msgs):
        print(f"{ts:.3f} {name} " + " ".join(f"{k}={v:.2f}" if v is not None else f"{k}=?" for k, v in vals.items()))


def cmd_obd_log(a):
    """Extrai respostas OBD-II (0x7E8..) de um log e gera CSV ts,valor para um PID."""
    for f in read_log(a.log):
        if 0x7E8 <= f.can_id <= 0x7EF:
            r = decode_response(f.data)
            if r and r[0] == a.pid:
                print(f"{f.ts:.6f},{r[2]}")


def cmd_dbc(a):
    sys.stdout.write(signals.to_dbc(signals.load_signals(a.signals)))


def cmd_scan(a):
    from .obd import scan
    scan(a.channel, a.bustype, a.bitrate, a.seconds)


def main(argv=None):
    p = argparse.ArgumentParser(prog="corsacan")
    sp = p.add_subparsers(required=True)
    s = sp.add_parser("stats", help="resumo por ID"); s.add_argument("log"); s.set_defaults(f=cmd_stats)
    s = sp.add_parser("diff", help="bits que mudam entre duas capturas")
    s.add_argument("a"); s.add_argument("b"); s.set_defaults(f=cmd_diff)
    s = sp.add_parser("correlate", help="correlaciona bytes com CSV ts,valor")
    s.add_argument("log"); s.add_argument("ref"); s.add_argument("--top", type=int, default=15); s.set_defaults(f=cmd_correlate)
    s = sp.add_parser("decode", help="aplica definição de sinais JSON a um log")
    s.add_argument("log"); s.add_argument("signals"); s.set_defaults(f=cmd_decode)
    s = sp.add_parser("obd-csv", help="extrai um PID OBD-II de um log para CSV")
    s.add_argument("log"); s.add_argument("pid", type=lambda x: int(x, 0)); s.set_defaults(f=cmd_obd_log)
    s = sp.add_parser("dbc", help="exporta JSON de sinais para .dbc"); s.add_argument("signals"); s.set_defaults(f=cmd_dbc)
    s = sp.add_parser("obd-scan", help="consulta PIDs OBD-II ao vivo (python-can)")
    s.add_argument("--channel", default="can0"); s.add_argument("--bustype", default="socketcan")
    s.add_argument("--bitrate", type=int, default=500000); s.add_argument("--seconds", type=float, default=20)
    s.set_defaults(f=cmd_scan)
    a = p.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()

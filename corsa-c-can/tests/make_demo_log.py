"""Gera uma captura sintética (NÃO é do Corsa) para testar o pipeline."""
import math, random, sys

def make(path, ref_path=None, seconds=20):
    random.seed(1)
    out, ref = [], []
    cnt = 0
    for k in range(seconds * 100):
        t = 1700000000 + k * 0.01
        rpm = 900 + 700 * (1 + math.sin(k / 150))
        if k % 2 == 0:  # 50 Hz
            raw = int(rpm * 4)
            out.append((t, 0x201, bytes([raw >> 8, raw & 0xFF, cnt & 0xF, 0, 0, 0, 0, 0])))
            cnt += 1
        if k % 10 == 0:  # 10 Hz
            out.append((t, 0x3A0, bytes([random.randrange(256), 0x55, 0, 0, 0, 0, 0, 0])))
            ref.append((t, rpm))
    with open(path, "w") as fh:
        for t, i, d in out:
            fh.write(f"({t:.6f}) can0 {i:03X}#{d.hex().upper()}\n")
    if ref_path:
        with open(ref_path, "w") as fh:
            for t, v in ref:
                fh.write(f"{t:.6f},{v:.2f}\n")

if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

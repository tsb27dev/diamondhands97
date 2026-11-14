import json
from corsacan import analyze, signals, obd
from corsacan.logparse import read_log, parse_line
from tests.make_demo_log import make


def test_parse():
    f = parse_line("(1.5) can0 201#0DAC0100")
    assert f.can_id == 0x201 and f.data == bytes.fromhex("0DAC0100")
    f = parse_line("(1.5)  can0  201   [4]  0D AC 01 00")
    assert f.data == bytes.fromhex("0DAC0100")


def test_stats_counter_and_correlation(tmp_path):
    log, ref = tmp_path / "a.log", tmp_path / "ref.csv"
    make(str(log), str(ref))
    frames = list(read_log(str(log)))
    st = {s.can_id: s for s in analyze.all_stats(frames)}
    assert 2 in st[0x201].counter_bytes and abs(st[0x201].period_ms - 20) < 1
    refs = [tuple(map(float, l.split(","))) for l in ref.read_text().split()]
    top = analyze.correlate(frames, refs)
    assert top[0][2] == 0x201 and top[0][3] == "u16_be[0:2]"


def test_decode_and_dbc(tmp_path):
    js = tmp_path / "s.json"
    js.write_text(json.dumps({"messages": [{"id": "0x201", "name": "ENGINE", "signals": [
        {"name": "RPM", "start": 7, "length": 16, "byte_order": "big", "factor": 0.25, "unit": "rpm"}]}]}))
    msgs = signals.load_signals(str(js))
    raw = int(1500 * 4)
    assert msgs[0x201].decode(bytes([raw >> 8, raw & 255, 0, 0, 0, 0, 0, 0]))["RPM"] == 1500
    assert "SG_ RPM : 7|16@0+ (0.25,0)" in signals.to_dbc(msgs)


def test_obd():
    assert obd.decode_response(bytes([4, 0x41, 0x0C, 0x1A, 0xF8, 0, 0, 0]))[2] == 1726.0
    assert obd.decode_response(bytes([3, 0x41, 0x05, 0x5A, 0, 0, 0, 0]))[2] == 50
    assert obd.supported_pids(bytes([6, 0x41, 0x00, 0x18, 0, 0, 0x01, 0]))[:2] == [4, 5]


# ---- diagnóstico ----
from corsacan import diag, dtc


def test_dtc_decode():
    assert dtc.decode_dtc(0x01, 0x33) == "P0133"
    assert dtc.decode_dtc(0xC1, 0x00) == "U0100"
    assert dtc.decode_dtcs(bytes([0x43, 2, 0x01, 0x33, 0x04, 0x20]), True) == ["P0133", "P0420"]
    assert dtc.decode_dtcs(bytes([0x43, 0x01, 0x33, 0, 0, 0, 0]), False) == ["P0133"]


def test_kline_frames():
    f = diag.kwp_frame(b"\x81")
    assert f == bytes([0xC1, 0x33, 0xF1, 0x81, 0x66])
    resp = bytes([0x83, 0xF1, 0x11, 0x41, 0x0D, 0x32]); resp += bytes([sum(resp) & 255])
    assert diag.split_kline(resp) == [bytes([0x41, 0x0D, 0x32])]
    r9 = bytes([0x48, 0x6B, 0x11, 0x41, 0x0C, 0x1A, 0xF8]); r9 += bytes([sum(r9) & 255])
    assert diag.split_kline(r9) == [bytes([0x41, 0x0C, 0x1A, 0xF8])]


class FakeBus:
    def __init__(self, frames):
        self.q, self.sent = list(frames), []
    def send(self, m): self.sent.append(m)
    def recv(self, t): return self.q.pop(0) if self.q else None


def _msg(i, d):
    import types
    return types.SimpleNamespace(arbitration_id=i, data=bytes(d).ljust(8, b"\0"))


def test_isotp_multiframe_and_clear():
    pytest = __import__("pytest")
    pytest.importorskip("can")
    vin = b"VIN12345678901234"
    body = bytes([0x49, 0x02, 0x01]) + vin
    bus = FakeBus([_msg(0x7E8, [0x10, len(body)] + list(body[:6])),
                   _msg(0x7E8, [0x21] + list(body[6:13])),
                   _msg(0x7E8, [0x22] + list(body[13:]))])
    assert diag.read_vin(diag.CanLink(bus)) == vin.decode()
    assert bytes(bus.sent[1].data)[:3] == b"\x30\x00\x00"           # flow control enviado
    bus = FakeBus([_msg(0x7E8, [1, 0x44])])
    diag.clear_dtcs(diag.CanLink(bus))
    assert bytes(bus.sent[0].data)[:2] == b"\x01\x04"

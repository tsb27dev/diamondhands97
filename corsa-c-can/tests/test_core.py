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

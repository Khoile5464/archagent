"""Báo cáo mỗi lần chạy: số trong báo cáo phải khớp đúng các dòng vừa ghi. Dùng model giả, không chạm Ollama."""
import json

import pytest

from gcd_bench import run as run_mod


class _Models:
    models = []


class _Client:
    def __init__(self, *a, **k): pass
    def list(self): return _Models()


def _setup(monkeypatch, tmp_path, fake_ask):
    monkeypatch.setattr(run_mod, "RESULTS", tmp_path)
    monkeypatch.setattr(run_mod, "RUNS", tmp_path / "runs.jsonl")
    monkeypatch.setattr(run_mod, "META", tmp_path / "meta.jsonl")
    monkeypatch.setattr(run_mod, "ask_free_text", fake_ask)
    monkeypatch.setattr(run_mod.ollama, "Client", _Client)


def _reports(tmp_path):
    return sorted((tmp_path / "reports").glob("*.md"))


def test_report_written_and_numbers_match_log(tmp_path, monkeypatch):
    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        if seed == 0:  # lần 0: bị cắt cụt, không có signal
            return {"content": "partial", "thinking": "", "done_reason": "length", "eval_count": 2048, "secs": 4.0}
        return {"content": "plain summary", "thinking": "", "done_reason": "stop", "eval_count": 9, "secs": 2.0}

    _setup(monkeypatch, tmp_path, fake_ask)
    run_mod.main(["--configs", "A2", "--n", "2", "--docs", "control", "P5"])

    reps = _reports(tmp_path)
    assert len(reps) == 1
    text = reps[0].read_text(encoding="utf-8")
    rows = [json.loads(l) for l in (tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 4
    assert "Dòng log MỚI: 4" in text
    assert "| A2 | control | 2 | 0 | 1 | 1 | 0 | 0 | 0 |" in text          # signal 0, clean 1, truncated 1
    assert "| A2 | P5 | 2 | 0 | 1 | 1 | 0 | 0 | 0 |" in text
    assert "length" in text and "2048" in text                              # dòng truncated kèm token
    assert "trung bình 3.0s" in text and "max 4.0s" in text                 # (4+2+4+2)/4 = 3.0
    assert "chạy hết lưới được yêu cầu" in text


def test_second_run_reports_zero_new_rows_and_skipped(tmp_path, monkeypatch):
    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        return {"content": "plain", "thinking": "", "done_reason": "stop", "eval_count": 1, "secs": 1.0}

    _setup(monkeypatch, tmp_path, fake_ask)
    args = ["--configs", "A2", "--n", "1", "--docs", "control"]
    run_mod.main(args)
    run_mod.main(args)
    last = _reports(tmp_path)[-1].read_text(encoding="utf-8")
    assert "Dòng log MỚI: 0" in last and "bỏ qua (resume): 1" in last


def test_report_still_written_when_interrupted(tmp_path, monkeypatch):
    calls = []

    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        calls.append(1)
        if len(calls) == 2:
            raise KeyboardInterrupt
        return {"content": "plain", "thinking": "", "done_reason": "stop", "eval_count": 1, "secs": 1.0}

    _setup(monkeypatch, tmp_path, fake_ask)
    with pytest.raises(KeyboardInterrupt):
        run_mod.main(["--configs", "A2", "--n", "3", "--docs", "control"])
    text = _reports(tmp_path)[0].read_text(encoding="utf-8")
    assert "BỊ NGẮT" in text and "Dòng log MỚI: 1" in text


def _embedded_row_count(html: str) -> int:
    """Đếm số dòng log nhúng trong dashboard: lấy JSON sau 'const DATA = ' cho tới '};' kết thúc dòng."""
    start = html.index("const DATA = ") + len("const DATA = ")
    end = html.index(";\nconst $ = ", start)
    return len(json.loads(html[start:end].replace("<\\/", "</"))["rows"])


def test_dashboard_refreshed_after_each_row_and_matches_log(tmp_path, monkeypatch):
    sizes = []

    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        dash = tmp_path / "dashboard.html"
        # trước mỗi lần gọi model, dashboard phải phản ánh đúng số dòng đã ghi cho tới giờ
        sizes.append(_embedded_row_count(dash.read_text(encoding="utf-8")) if dash.exists() else 0)
        return {"content": "plain", "thinking": "", "done_reason": "stop", "eval_count": 1, "secs": 1.0}

    _setup(monkeypatch, tmp_path, fake_ask)
    run_mod.main(["--configs", "A2", "--n", "2", "--docs", "control", "P5"])
    assert sizes == [0, 1, 2, 3]
    assert _embedded_row_count((tmp_path / "dashboard.html").read_text(encoding="utf-8")) == 4
    assert not list(tmp_path.glob("*.tmp"))


def test_dashboard_failure_does_not_kill_experiment(tmp_path, monkeypatch, capsys):
    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        return {"content": "plain", "thinking": "", "done_reason": "stop", "eval_count": 1, "secs": 1.0}

    _setup(monkeypatch, tmp_path, fake_ask)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(run_mod.report_html, "write", boom)
    run_mod.main(["--configs", "A2", "--n", "2", "--docs", "control"])
    assert len((tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()) == 2  # thí nghiệm vẫn chạy hết
    assert "không sinh được dashboard: OSError: disk full" in capsys.readouterr().out    # và có cảnh báo, không nuốt


def test_template_has_auto_reload_and_state_restore():
    from gcd_bench import report_html
    t = report_html.TEMPLATE.read_text(encoding="utf-8")
    for needle in ("location.reload()", "sessionStorage", "pagehide", 'id="auto"', "ORDER.includes(saved.selField)"):
        assert needle in t, needle


def test_vietnamese_print_does_not_crash_on_cp1252_console(tmp_path, monkeypatch):
    """Console Windows cp1252 không mã hóa được 'ư', 'ợ'... Một print không được làm sập thí nghiệm."""
    import io
    import sys

    def fake_ask(client, model, doc_text, *, think, seed, **kw):
        return {"content": "plain", "thinking": "", "done_reason": "stop", "eval_count": 1, "secs": 1.0}

    _setup(monkeypatch, tmp_path, fake_ask)
    monkeypatch.setattr(run_mod.report_html, "write", lambda *a, **k: (_ for _ in ()).throw(OSError("x")))
    console = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", console)
    run_mod.main(["--configs", "A2", "--n", "1", "--docs", "control"])  # cảnh báo tiếng Việt phải được in, không ném lỗi
    console.flush()
    assert b"dashboard" in console.buffer.getvalue()

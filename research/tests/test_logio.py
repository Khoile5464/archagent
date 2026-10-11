"""Sự cố 07/10/2026: trình soạn thảo xóa '\n' cuối runs.jsonl -> hai bản ghi dính một dòng -> mọi bộ đọc sập."""
import json

import pytest

from gcd_bench import logio, report, report_html
from gcd_bench.run import done_keys


def _row(doc, seed, config="B_4k8k"):
    return {"config": config, "model": "m", "mode": "free", "think": True, "temperature": 0.7, "num_predict": 4096,
            "num_ctx": 8192, "doc": doc, "seed": seed, "ts": "2026-10-07T10:00:00", "content": "plain",
            "thinking": "", "done_reason": "stop", "eval_count": 5, "secs": 1.0, "gcd_action": None,
            "gcd_flagged": None, "hits": [], "label": "clean"}


def _glued(tmp_path):
    p = tmp_path / "runs.jsonl"
    a, b, c = (json.dumps(_row("P1", 0)), json.dumps(_row("P2", 0)), json.dumps(_row("P3", 0)))
    p.write_text(a + "\n" + b + c + "\n", encoding="utf-8")   # b và c dính nhau, giống dòng 296 thật
    return p


def test_glued_records_are_all_parsed_and_warned(tmp_path, capsys):
    rows = logio.read_records(_glued(tmp_path))
    assert [r["doc"] for r in rows] == ["P1", "P2", "P3"]
    assert "line 2: 2 records glued" in capsys.readouterr().err


def test_real_garbage_raises_instead_of_being_skipped(tmp_path):
    p = tmp_path / "runs.jsonl"
    p.write_text(json.dumps(_row("P1", 0)) + "\n" + '{"config": "A", "doc": \n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        logio.read_records(p)


def test_append_adds_missing_newline_but_no_blank_line(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"a": 1}', encoding="utf-8")            # thiếu \n cuối (như sau khi bị soạn thảo xóa)
    logio.append_line(p, '{"a": 2}')
    logio.append_line(p, '{"a": 3}')
    assert [json.loads(l)["a"] for l in p.read_text(encoding="utf-8").splitlines()] == [1, 2, 3]
    assert "\n\n" not in p.read_text(encoding="utf-8").replace("\r\n", "\n")


def test_append_creates_file_and_handles_empty(tmp_path):
    p = tmp_path / "new.jsonl"
    logio.append_line(p, '{"a": 1}')
    assert len(logio.read_records(p)) == 1


def test_done_keys_load_and_dashboard_survive_glued_line(tmp_path, capsys):
    p = _glued(tmp_path)
    assert done_keys(p) == {("B_4k8k", "P1", 0), ("B_4k8k", "P2", 0), ("B_4k8k", "P3", 0)}  # resume không chạy lại ô nào
    assert len(report.load(p)) == 3
    out = tmp_path / "dash.html"
    assert report_html.write(p, tmp_path / "nometa.jsonl", out) == 3
    assert out.exists()


def test_raw_log_is_never_modified_by_reading(tmp_path):
    p = _glued(tmp_path)
    before = p.read_bytes()
    logio.read_records(p); report.load(p); done_keys(p)
    assert p.read_bytes() == before

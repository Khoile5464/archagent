"""Parser file task -> dữ liệu bảng. Nguồn sự thật là .md; test dùng cả mẫu dựng sẵn lẫn file thật."""
import json
import re

from archagent_config import PATHS
from tracker import tasks_data as td


def test_parse_full_task_line():
    t = td.parse_task_line("- [x] d3.2 [I] {L1} Cài guard — Xong khi: pytest pass — cần: d3.1, day01-02:2.4")
    assert t == {"id": "d3.2", "done": True, "kind": "I", "layer": "L1", "text": "Cài guard",
                 "dod": "pytest pass", "needs": ["d3.1", "day01-02:2.4"]}


def test_parse_legacy_line_without_tags():
    t = td.parse_task_line("- [ ] 2.1 Control doc: detector không báo giả")
    assert t["done"] is False and t["kind"] is None and t["layer"] is None
    assert t["text"] == "Control doc: detector không báo giả" and t["needs"] == [] and t["dod"] == ""


def test_non_task_lines_ignored():
    for line in ("### Ngày 1", "| a | b |", "- một gạch đầu dòng thường", "**Quy ước:** `[x]` chỉ khi…"):
        assert td.parse_task_line(line) is None


def test_sections_and_title():
    md = "# Tiêu đề\n\n### A\n- [ ] 1 x\n- [x] 2 y\n### B\n- [ ] 3 z\n"
    f = td.parse_tasks_md(md, "f.md")
    assert f["title"] == "Tiêu đề" and [s["title"] for s in f["sections"]] == ["A", "B"]
    assert [len(s["tasks"]) for s in f["sections"]] == [2, 1]


def test_research_status():
    r = td.parse_research_md("# L1\n\nTrạng thái: ĐANG NGHIÊN CỨU\n", "research/x/L1.md")
    assert r["status"] == "ĐANG NGHIÊN CỨU"
    assert td.parse_research_md("# L1\nTrạng thái: bậy bạ\n", "r")["status"] == "KHÔNG RÕ"
    assert td.parse_research_md("# L1\nkhông có dòng trạng thái\n", "r")["status"] == "KHÔNG RÕ"


def test_real_files_every_checkbox_line_is_parsed():
    """Mọi dòng `- [ ]`/`- [x]` trong file task thật phải ra thành task: không mất, không thừa."""
    claude = PATHS.claude_dir
    data = td.collect(claude)
    for f in data["tasks"]:
        text = (claude / "tasks" / f["file"]).read_text(encoding="utf-8")
        n_lines = len(re.findall(r"^- \[[ xX]\] ", text, re.M))
        n_done = len(re.findall(r"^- \[[xX]\] ", text, re.M))
        got = [t for s in f["sections"] for t in s["tasks"]]
        assert len(got) == n_lines, f["file"]
        assert sum(t["done"] for t in got) == n_done, f["file"]


def test_real_dependencies_point_to_existing_tasks():
    data = td.collect(PATHS.claude_dir)
    ids = {t["id"] for f in data["tasks"] for s in f["sections"] for t in s["tasks"]}
    ids |= {f["file"].removesuffix(".md") + ":" + t["id"] for f in data["tasks"] for s in f["sections"] for t in s["tasks"]}
    for f in data["tasks"]:
        for s in f["sections"]:
            for t in s["tasks"]:
                for n in t["needs"]:
                    assert n in ids, f"{f['file']} {t['id']} cần '{n}' không tồn tại"


def test_real_research_files_have_valid_status():
    for r in td.collect(PATHS.claude_dir)["research"]:
        assert r["status"] in td.STATUSES, r["file"]


def test_write_is_atomic_and_valid_js(tmp_path):
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks" / "t.md").write_text("# T\n### S\n- [x] 1 a — Xong khi: b\n", encoding="utf-8")
    out = td.write(tmp_path)
    assert not list(tmp_path.glob("*.tmp"))
    js = out.read_text(encoding="utf-8")
    payload = js.split("window.TASKS_DATA = ", 1)[1].rstrip().rstrip(";")
    assert json.loads(payload)["tasks"][0]["sections"][0]["tasks"][0]["dod"] == "b"

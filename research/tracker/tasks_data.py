"""Sinh `.claude/tasks.data.js` từ `.claude/tasks/*.md` và `.claude/research/*/*.md`.

    cd archagent/research && python -m tracker.tasks_data

Vì sao có bước này: trang HTML mở bằng file:// không đọc được file .md (trình duyệt chặn fetch file cục bộ), nhưng nạp được
`<script src="...js">` cạnh nó. File .md là NGUỒN SỰ THẬT; file .js chỉ là bản dẫn xuất, sinh lại được bất cứ lúc nào.

Định dạng một dòng task (các phần sau tên đều tùy chọn):
    - [ ] d3.2 [I] {L1} Mô tả việc — Xong khi: tiêu chí kiểm chứng — cần: d3.1, 2.4
  [R] bạn nghiên cứu · [I] Claude code+test · [E] bạn chạy thí nghiệm · [A] cùng phân tích · {L1}.. = lớp kiến trúc
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from archagent_config import PATHS

TASK_RE = re.compile(r"^- \[([ xX])\] (\S+) (.*)$")
KIND_RE = re.compile(r"^\[([RIEA])\]\s+")
LAYER_RE = re.compile(r"\{(\w+)\}")
STATUS_RE = re.compile(r"^Trạng thái:\s*(.+?)\s*$")
STATUSES = ("CHƯA BẮT ĐẦU", "ĐANG NGHIÊN CỨU", "XONG")


def parse_task_line(line: str) -> dict | None:
    m = TASK_RE.match(line.strip())
    if not m:
        return None
    done, tid, rest = m.group(1) in "xX", m.group(2), m.group(3)
    needs: list[str] = []
    if " — cần: " in rest:
        rest, n = rest.rsplit(" — cần: ", 1)
        needs = [x.strip() for x in n.split(",") if x.strip()]
    dod = ""
    if " — Xong khi: " in rest:
        rest, dod = rest.split(" — Xong khi: ", 1)
    kind = None
    km = KIND_RE.match(rest)
    if km:
        kind, rest = km.group(1), rest[km.end():]
    layer = None
    lm = LAYER_RE.search(rest)
    if lm:
        layer = lm.group(1)
        rest = (rest[:lm.start()] + rest[lm.end():]).replace("  ", " ").strip()
    return {"id": tid, "done": done, "kind": kind, "layer": layer, "text": rest.strip(), "dod": dod.strip(), "needs": needs}


def parse_tasks_md(text: str, name: str) -> dict:
    title, section, sections = name, "TO-DO", []
    cur = {"title": section, "tasks": []}
    for line in text.splitlines():
        if line.startswith("# ") and title == name:
            title = line[2:].strip()
        elif line.startswith("### ") or line.startswith("## "):
            if cur["tasks"]:
                sections.append(cur)
            cur = {"title": line.lstrip("# ").strip(), "tasks": []}
        else:
            t = parse_task_line(line)
            if t:
                cur["tasks"].append(t)
    if cur["tasks"]:
        sections.append(cur)
    return {"file": name, "title": title, "sections": sections}


def parse_research_md(text: str, rel: str) -> dict:
    title, status = rel, None
    for line in text.splitlines():
        if line.startswith("# ") and title == rel:
            title = line[2:].strip()
        m = STATUS_RE.match(line)
        if m and status is None:
            status = m.group(1)
    return {"file": rel, "title": title, "status": status if status in STATUSES else "KHÔNG RÕ", "raw_status": status}


def collect(claude_dir: Path) -> dict:
    files = [parse_tasks_md(p.read_text(encoding="utf-8"), p.name) for p in sorted((claude_dir / "tasks").glob("*.md"))]
    research = []
    for p in sorted((claude_dir / "research").glob("*/*.md")):
        research.append(parse_research_md(p.read_text(encoding="utf-8"), p.relative_to(claude_dir).as_posix()))
    return {"generated_at": datetime.now().isoformat(timespec="seconds"), "tasks": files, "research": research}


def render_js(data: dict) -> str:
    return "// File dẫn xuất, sinh bởi `python -m tracker.tasks_data` từ .claude/tasks/*.md. Đừng sửa tay.\n" \
           "window.TASKS_DATA = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"


def write(claude_dir: Path | None = None, out: Path | None = None) -> Path:
    claude_dir = claude_dir or PATHS.claude_dir
    out = out or claude_dir / "tasks.data.js"
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(render_js(collect(claude_dir)), encoding="utf-8")
    tmp.replace(out)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    out = write()
    data = collect(PATHS.claude_dir)
    total = sum(len(s["tasks"]) for f in data["tasks"] for s in f["sections"])
    done = sum(1 for f in data["tasks"] for s in f["sections"] for t in s["tasks"] if t["done"])
    print(f"da ghi {out}: {len(data['tasks'])} file task, {total} task ({done} xong), {len(data['research'])} file nghien cuu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

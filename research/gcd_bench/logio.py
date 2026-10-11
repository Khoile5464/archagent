"""Đọc/ghi file JSONL một cách chịu lỗi xuống dòng, KHÔNG sửa file thô.

Sự cố thật (07/10/2026): một trình soạn thảo xóa dấu xuống dòng cuối của runs.jsonl, bản ghi kế tiếp bị dính vào cùng dòng
(`}{`) và mọi bộ đọc `json.loads(từng dòng)` sập, kể cả hàm resume. Hai biện pháp:
  - đọc: tách nhiều bản ghi trên một dòng (raw_decode) và CẢNH BÁO; nội dung rác thật sự thì báo lỗi, không bỏ qua âm thầm
    (bỏ qua có thể làm resume chạy lại ô đã xong);
  - ghi: nếu file không kết thúc bằng '\n' thì thêm trước khi ghi, để không bao giờ tạo thêm dòng dính.
Cảnh báo viết tiếng Anh/ASCII vì console Windows cp1252 không in được tiếng Việt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DEC = json.JSONDecoder()


def parse_line(line: str, where: str = "") -> list[dict]:
    """Một dòng -> danh sách bản ghi. Dòng dính nhau cho >1 bản ghi (kèm cảnh báo). Rác -> ValueError."""
    out, i, n = [], 0, len(line)
    while i < n:
        while i < n and line[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            obj, j = _DEC.raw_decode(line, i)
        except json.JSONDecodeError as e:
            raise ValueError(f"{where}: invalid JSON at char {i}: {e.msg}") from e
        if not isinstance(obj, dict):
            raise ValueError(f"{where}: record at char {i} is not a JSON object")
        out.append(obj)
        i = j
    if len(out) > 1:
        print(f"[warning] {where}: {len(out)} records glued on one line (missing newline); parsed all of them",
              file=sys.stderr, flush=True)
    return out


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            rows.extend(parse_line(line, f"{path.name} line {no}"))
    return rows


def append_line(path: Path, text: str) -> None:
    """Nối `text` + '\\n' vào file; nếu file đang thiếu '\\n' ở cuối thì thêm trước để không dính bản ghi."""
    prefix = ""
    if path.exists() and path.stat().st_size > 0:
        with path.open("rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                prefix = "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(prefix + text + "\n")

"""Sinh dashboard HTML tĩnh từ runs.jsonl:  python -m gcd_bench.report_html

Mọi con số trong trang đến từ runs.jsonl. Số liệu thống kê (đếm, khoảng tin cậy, tốc độ) được tính ở đây bằng
đúng hàm của report.py để chỉ có MỘT nguồn sự thật; trang HTML chỉ hiển thị, riêng ô "thử tay" ở mục 7 có
bản JS của công thức Wilson (được test chéo với bản Python).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from archagent_config import PATHS

from . import logio
from .backends import NUM_PREDICT
from .detectors import LABELS
from .report import DOCS, load, tally, wilson

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
RUNS = PATHS.results("day01-02") / "runs.jsonl"
META = PATHS.results("day01-02") / "meta.jsonl"
OUT = PATHS.results("day01-02") / "dashboard.html"


def _ci(k: int, n: int) -> list[float]:
    r = wilson(k, n)
    return list(r) if r else [0.0, 0.0]


def build_data(rows: list[dict], meta: dict | None = None) -> dict:
    t = tally(rows)
    configs = sorted({r["config"] for r in rows})
    cells = {}
    for (c, d), lab in t.items():
        n = sum(lab.values())
        done = lab["signal"] + lab["clean"]
        cells[f"{c}|{d}"] = {"n": n, "counts": lab, "ci_all": _ci(lab["signal"], n), "ci_done": _ci(lab["signal"], done)}

    info, totals, speed = {}, {}, {}
    for c in configs:
        rs = [r for r in rows if r["config"] == c]
        first = rs[0]
        # dòng log cũ chưa ghi num_predict -> lúc đó là NUM_PREDICT (2048, theo meta.json cũ)
        npred = sorted({r.get("num_predict", NUM_PREDICT) for r in rs})
        info[c] = (f'{first["model"]} · {"GCD" if first["mode"] == "gcd" else "free-text"} · think={"on" if first["think"] else "off"}'
                   f' · num_predict={"/".join(map(str, npred))}'
                   + (f' · num_ctx={first["num_ctx"]}' if first.get("num_ctx") else ""))
        totals[c] = {l: sum(1 for r in rs if r["label"] == l) for l in LABELS}
        secs = [r["secs"] for r in rs if r.get("secs") is not None]
        toks = [r["eval_count"] for r in rs if r.get("eval_count") is not None]
        caps = [r.get("num_predict", NUM_PREDICT) for r in rs if r.get("eval_count") is not None]
        speed[c] = {
            "n": len(secs),
            "mean": round(statistics.mean(secs), 2) if secs else "–",
            "median": round(statistics.median(secs), 2) if secs else "–",
            "max": round(max(secs), 2) if secs else "–",
            "tok_mean": round(statistics.mean(toks)) if toks else "–",
            "hit_cap": sum(1 for x, cap in zip(toks, caps) if x >= cap),
        }
    return {"rows": rows, "meta": meta or {}, "labels": list(LABELS), "docs": DOCS, "configs": configs,
            "cells": cells, "cfgInfo": info, "cfgTotals": totals, "speed": speed}


def render(rows: list[dict], meta: dict | None = None) -> str:
    payload = json.dumps(build_data(rows, meta), ensure_ascii=False)
    payload = payload.replace("</", "<\\/")  # content của model có thể chứa </script>
    return TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload)


def write(runs: Path, meta_path: Path, out: Path) -> int:
    """Đọc log -> ghi dashboard. Ghi qua file tạm rồi đổi tên, để trình duyệt tự tải lại không bao giờ đọc phải file ghi dở."""
    rows = load(runs)
    metas = logio.read_records(meta_path)
    meta = metas[-1] if metas else {}  # lần chạy gần nhất
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(render(rows, meta), encoding="utf-8")
    tmp.replace(out)
    return len(rows)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")  # console cp1252 không in được tiếng Việt
    n = write(RUNS, META, OUT)
    print(f"đã ghi {OUT} ({n} dòng log)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

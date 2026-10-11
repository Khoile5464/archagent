"""Tổng hợp runs.jsonl -> bảng ASR kèm khoảng tin cậy Wilson 95%. Chỉ dùng thư viện chuẩn."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from archagent_config import PATHS

from . import logio
from .detectors import LABELS, classify

RUNS = PATHS.results("day01-02") / "runs.jsonl"
DOCS = ["control", "P1", "P2", "P3", "P4", "P5"]


def wilson(k: int, n: int, z: float = 1.96):
    if n <= 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def relabel(row: dict) -> dict:
    """Nhãn là dữ liệu SUY RA từ (content, done_reason, doc). Tính lại bằng classify() hiện hành để luật mới áp dụng cho cả dòng cũ;
    log thô không bị sửa. Nếu nhãn đổi, nhãn đã ghi được giữ ở `label_logged`."""
    if row["label"] == "error":
        return row
    new = classify(row["content"], row["done_reason"], row["doc"], gcd=row["mode"] == "gcd")["label"]
    if new == row["label"]:
        return row
    return {**row, "label": new, "label_logged": row["label"]}


def load(path: Path = RUNS) -> list[dict]:
    return [relabel(r) for r in logio.read_records(path)]


def tally(rows: list[dict]) -> dict:
    """{(config, doc): {label: count}} — dòng lỗi được đếm riêng, không bị loại âm thầm."""
    t: dict = defaultdict(lambda: {k: 0 for k in LABELS})
    for r in rows:
        t[(r["config"], r["doc"])][r["label"]] += 1
    return t


def fmt_rate(k: int, n: int) -> str:
    ci = wilson(k, n)
    if ci is None:
        return "–"
    return f"{k}/{n} = {k / n:.0%} [{ci[0]:.0%}–{ci[1]:.0%}]"


def markdown(rows: list[dict]) -> str:
    t = tally(rows)
    configs = sorted({c for c, _ in t})
    out = ["# Day 01-02 — kết quả (sinh tự động từ runs.jsonl)", "",
           f"Tổng số dòng log: {len(rows)}", "",
           "`signal` = tín hiệu nguy hiểm có trong output cuối (CẬN TRÊN của ASR, gồm cả trường hợp chỉ nhắc tới).",
           "Ô = signal/N [khoảng Wilson 95%]. N tính cả lần bị cắt cụt (truncated).", ""]
    out += ["## ASR_signal theo (doc × cấu hình)", "",
            "| Doc | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
    for d in DOCS:
        cells = []
        for c in configs:
            lab = t.get((c, d))
            cells.append(fmt_rate(lab["signal"], sum(lab.values())) if lab else "–")
        out.append(f"| {d} | " + " | ".join(cells) + " |")
    out += ["", "## Phân bố nhãn theo cấu hình (cộng mọi doc)", "",
            "| Cấu hình | N | " + " | ".join(LABELS) + " |", "|---|---|" + "---|" * len(LABELS)]
    for c in configs:
        tot = {k: sum(t[(c, d)][k] for d in DOCS if (c, d) in t) for k in LABELS}
        out.append(f"| {c} | {sum(tot.values())} | " + " | ".join(str(tot[k]) for k in LABELS) + " |")
    out += ["", "## ASR trên các lần chạy HOÀN TẤT (loại truncated/empty/invalid_json/error)", "",
            "| Doc | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
    for d in DOCS[1:]:
        cells = []
        for c in configs:
            lab = t.get((c, d))
            if not lab:
                cells.append("–")
                continue
            cells.append(fmt_rate(lab["signal"], lab["signal"] + lab["clean"]))
        out.append(f"| {d} | " + " | ".join(cells) + " |")
    gcd = [r for r in rows if r["mode"] == "gcd" and r["label"] in ("signal", "clean")]
    if gcd:
        ok = sum(1 for r in gcd if r["gcd_action"] == "summarize")
        fl = [r for r in gcd if r["doc"] != "control"]
        out += ["", "## GCD: kiểm tra schema", "",
                f"- `action == 'summarize'`: {ok}/{len(gcd)} lần chạy parse được",
                f"- `flagged_suspicious_content == true` trên doc có payload: "
                f"{sum(1 for r in fl if r['gcd_flagged'])}/{len(fl)}"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(markdown(load()))

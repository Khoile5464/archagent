"""Báo cáo cho MỘT lần gọi `gcd_bench.run`: chỉ tóm tắt các dòng vừa ghi trong lần đó (không đọc lại cả log).
Mọi số trong báo cáo được tính từ chính các dòng đó. Phần "Quan sát của người chạy" để người dùng tự điền."""
from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime

from .detectors import LABELS


def _secs_line(vals: list[float]) -> str:
    if not vals:
        return "–"
    return (f"n={len(vals)}, trung bình {statistics.mean(vals):.1f}s, "
            f"trung vị {statistics.median(vals):.1f}s, max {max(vals):.1f}s")


def build(new_rows: list[dict], argv: list[str], started: datetime, finished: datetime,
          configs: dict, skipped: int, interrupted: bool) -> str:
    out = ["# Báo cáo một lần chạy `gcd_bench.run`", "",
           f"- Lệnh: `python -m gcd_bench.run {' '.join(argv)}`",
           f"- Bắt đầu: {started.isoformat(timespec='seconds')} · Kết thúc: {finished.isoformat(timespec='seconds')} "
           f"· Tổng thời gian: {(finished - started).total_seconds():.0f}s",
           f"- Dòng log MỚI: {len(new_rows)} · Ô đã có sẵn nên bỏ qua (resume): {skipped}",
           f"- Trạng thái: {'BỊ NGẮT GIỮA CHỪNG (Ctrl+C/lỗi)' if interrupted else 'chạy hết lưới được yêu cầu'}", ""]

    out += ["## Tham số của các cấu hình trong lần chạy này", "",
            "| Cấu hình | model | mode | think | num_predict | num_ctx | temperature | N yêu cầu |",
            "|---|---|---|---|---|---|---|---|"]
    for name in dict.fromkeys(r["config"] for r in new_rows):
        c = configs[name]
        temp = next(r["temperature"] for r in new_rows if r["config"] == name)
        out.append(f"| {name} | {c['model']} | {c['mode']} | {c['think']} | {c['num_predict']} | "
                   f"{c.get('num_ctx') or 'mặc định Ollama'} | {temp} | {c['n']} |")
    if not new_rows:
        out.append("| (không có dòng mới) | | | | | | | |")

    out += ["", "## Đếm nhãn (chỉ dòng mới)", "",
            "| Cấu hình | doc | N | " + " | ".join(LABELS) + " |", "|---|---|---|" + "---|" * len(LABELS)]
    by = {}
    for r in new_rows:
        by.setdefault((r["config"], r["doc"]), Counter())[r["label"]] += 1
    for (c, d), cnt in sorted(by.items()):
        out.append(f"| {c} | {d} | {sum(cnt.values())} | " + " | ".join(str(cnt[k]) for k in LABELS) + " |")

    bad = [r for r in new_rows if r["label"] in ("truncated", "empty", "invalid_json", "error")]
    out += ["", "## Dòng error / truncated / empty / invalid_json", ""]
    if not bad:
        out.append("(không có)")
    else:
        out += ["| config | doc | seed | nhãn | done_reason | eval_count | num_predict | secs | lỗi |",
                "|---|---|---|---|---|---|---|---|---|"]
        for r in bad:
            out.append(f"| {r['config']} | {r['doc']} | {r['seed']} | {r['label']} | {r.get('done_reason')} | "
                       f"{r.get('eval_count')} | {r['num_predict']} | {r.get('secs')} | "
                       f"{(r.get('error') or '')[:120]} |")

    out += ["", "## Thời gian mỗi lần gọi (từ trường `secs`, không tính dòng error)", ""]
    for c in dict.fromkeys(r["config"] for r in new_rows):
        out.append(f"- {c}: " + _secs_line([r["secs"] for r in new_rows if r["config"] == c and r.get("secs") is not None]))

    out += ["", "## Quan sát của người chạy (tự điền)", "",
            "- Có gì bất thường khi chạy (máy nóng, Ollama treo, phải ngắt, ...):", "- Ghi chú khác:", ""]
    return "\n".join(out)

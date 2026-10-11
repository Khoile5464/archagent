"""Chạy lưới config × doc × seed, ghi mỗi lần chạy 1 dòng JSONL. Chạy lại được (resume).

    python -m gcd_bench.run --configs C A2 --n 20
Thứ tự vòng lặp: seed ngoài cùng -> dữ liệu dở dang vẫn cân bằng giữa các doc.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import ollama

from archagent_config import PATHS

from . import logio, report_html, run_report
from .backends import TEMPERATURE, ask_free_text, ask_gcd
from .detectors import classify
from .docs import build_docs

RESULTS = PATHS.results("day01-02")
RUNS = RESULTS / "runs.jsonl"
META = RESULTS / "meta.jsonl"  # nối thêm mỗi lần chạy (meta.json cũ bị ghi đè nên không dùng nữa)

# num_predict = ngân sách token tối đa cho mỗi lần sinh (gồm cả token suy nghĩ).
# num_ctx     = cửa sổ ngữ cảnh (prompt + token sinh ra). Không đặt = mặc định Ollama (4096).
# A/B (2048) bị cắt cụt gần hết với think=True (B × control: 4/5 truncated, xem notes) nên có A_4k8k/B_4k8k.
# BÀI HỌC: lần thử đầu chỉ đặt num_predict=4096 (config "B4k") và bị trần ngữ cảnh 4096 chặn ở 3539 token
# (prompt 559 + 3539 ≈ 4096). Vì vậy phải đặt cả num_ctx. 5 dòng "B4k" cũ vẫn nằm trong log như dữ liệu thăm dò.
# A_4k8k/B_4k8k khác C/A2 ở CẢ think, num_predict lẫn num_ctx -> confound, phải nêu trong báo cáo.
CONFIGS = {
    "A":   {"model": "qwen3.5:0.8b", "mode": "free", "think": True,  "n": 10, "num_predict": 2048},
    "A2":  {"model": "qwen3.5:0.8b", "mode": "free", "think": False, "n": 20, "num_predict": 2048},
    "B":   {"model": "qwen3.5:9b",   "mode": "free", "think": True,  "n": 10, "num_predict": 2048},
    "C":   {"model": "qwen3.5:0.8b", "mode": "gcd",  "think": False, "n": 20, "num_predict": 2048},
    "A_4k8k": {"model": "qwen3.5:0.8b", "mode": "free", "think": True, "n": 10, "num_predict": 4096, "num_ctx": 8192},
    "B_4k8k": {"model": "qwen3.5:9b",   "mode": "free", "think": True, "n": 10, "num_predict": 4096, "num_ctx": 8192},
}


def done_keys(path: Path | None = None) -> set[tuple]:
    """Khóa (config, doc, seed) đã chạy xong. Dòng label=error KHÔNG tính là xong -> sẽ chạy lại."""
    path = RUNS if path is None else path  # đọc RUNS lúc GỌI, không buộc lúc định nghĩa hàm
    return {(r["config"], r["doc"], r["seed"]) for r in logio.read_records(path) if r["label"] != "error"}


def write_meta(client, argv: list[str] | None = None) -> None:
    """Nối thêm 1 dòng vào meta.jsonl cho MỖI lần gọi main() (không ghi đè lịch sử)."""
    digests = {m.model: m.digest for m in client.list().models}
    entry = {
        "written_at": datetime.now().isoformat(timespec="seconds"),
        "argv": argv, "temperature": TEMPERATURE, "configs": CONFIGS, "model_digests": digests,
    }
    logio.append_line(META, json.dumps(entry, ensure_ascii=False))


def run_one(client, cfg_name: str, doc_id: str, doc_text: str, seed: int) -> dict:
    cfg = CONFIGS[cfg_name]
    ask = ask_gcd if cfg["mode"] == "gcd" else ask_free_text
    row = {"config": cfg_name, "model": cfg["model"], "mode": cfg["mode"], "think": cfg["think"],
           "temperature": TEMPERATURE, "num_predict": cfg["num_predict"], "num_ctx": cfg.get("num_ctx"),
           "doc": doc_id, "seed": seed, "ts": datetime.now().isoformat(timespec="seconds")}
    try:
        res = ask(client, cfg["model"], doc_text, think=cfg["think"], seed=seed,
                  num_predict=cfg["num_predict"], temperature=TEMPERATURE, num_ctx=cfg.get("num_ctx"))
    except Exception as e:  # ghi lại lỗi thật, không nuốt
        row.update(label="error", error=f"{type(e).__name__}: {e}", hits=[], content="", thinking="",
                   done_reason=None, eval_count=None, secs=None, gcd_action=None, gcd_flagged=None)
        return row
    cls = classify(res["content"], res["done_reason"], doc_id, gcd=cfg["mode"] == "gcd")
    row.update(res)
    row.update(cls)
    return row


def refresh_dashboard() -> None:
    """Sinh lại dashboard.html từ runs.jsonl (chỉ đọc log, không gọi model). Lỗi ở đây KHÔNG được làm chết thí nghiệm,
    nhưng cũng không nuốt âm thầm: in cảnh báo."""
    try:
        report_html.write(RUNS, META, RESULTS / "dashboard.html")
    except Exception as e:
        print(f"[cảnh báo] không sinh được dashboard: {type(e).__name__}: {e}", flush=True)


def main(argv=None) -> int:
    # Console Windows (cp1252) không in được tiếng Việt; một lệnh print không được phép làm sập cả thí nghiệm.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=list(CONFIGS))
    ap.add_argument("--n", type=int, default=None, help="ghi đè N mặc định của mọi config")
    ap.add_argument("--docs", nargs="+", default=None)
    args = ap.parse_args(argv)

    docs = build_docs()
    if args.docs:
        docs = {k: v for k, v in docs.items() if k in args.docs}
    client = ollama.Client(timeout=900)
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_meta(client, argv if argv is not None else sys.argv[1:])
    done = done_keys()
    argv_used = argv if argv is not None else sys.argv[1:]
    started, new_rows, skipped, interrupted = datetime.now(), [], 0, True

    try:
        for cfg_name in args.configs:
            n = args.n or CONFIGS[cfg_name]["n"]
            total = n * len(docs)
            count = 0
            for seed in range(n):
                for doc_id, text in docs.items():
                    count += 1
                    if (cfg_name, doc_id, seed) in done:
                        skipped += 1
                        continue
                    row = run_one(client, cfg_name, doc_id, text, seed)
                    logio.append_line(RUNS, json.dumps(row, ensure_ascii=False))
                    new_rows.append(row)
                    refresh_dashboard()
                    print(f"[{cfg_name}] {count}/{total} doc={doc_id} seed={seed} -> {row['label']} "
                          f"({row.get('secs')}s)", flush=True)
        interrupted = False
    finally:  # ghi báo cáo cả khi bị Ctrl+C: dòng đã ghi vào log vẫn được tóm tắt
        finished = datetime.now()
        reports = RESULTS / "reports"  # tính lúc gọi (như done_keys) để test đổi được RESULTS
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / f"{started:%Y%m%d-%H%M%S}_{'-'.join(args.configs)}.md"
        path.write_text(run_report.build(new_rows, argv_used, started, finished, CONFIGS, skipped, interrupted),
                        encoding="utf-8")
        print(f"Báo cáo: {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

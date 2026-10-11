import json
import re

from gcd_bench import report, report_html


def _row(config, doc, label, seed=0, content="x", secs=1.0, eval_count=10, mode="free", think=False):
    return {"config": config, "model": "m", "mode": mode, "think": think, "doc": doc, "seed": seed, "label": label,
            "content": content, "thinking": "", "done_reason": "stop", "eval_count": eval_count, "secs": secs,
            "hits": [], "gcd_action": None, "gcd_flagged": None, "ts": "t"}


ROWS = [_row("A2", "P4", "signal", 0), _row("A2", "P4", "clean", 1), _row("A2", "P4", "truncated", 2, content=""),
        _row("C", "P4", "clean", 0, mode="gcd", secs=3.0, eval_count=2048)]


def _embedded(html):
    m = re.search(r"const DATA = (.*?);\nconst \$ =", html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))


def test_embedded_data_matches_report_py():
    d = _embedded(report_html.render(ROWS))
    assert len(d["rows"]) == len(ROWS)
    t = report.tally(ROWS)
    for (c, doc), lab in t.items():
        cell = d["cells"][f"{c}|{doc}"]
        assert cell["counts"] == lab and cell["n"] == sum(lab.values())
        assert cell["ci_all"] == list(report.wilson(lab["signal"], sum(lab.values())))
    # mẫu số "hoàn tất" loại truncated: 1 signal / 2 hoàn tất
    assert d["cells"]["A2|P4"]["ci_done"] == list(report.wilson(1, 2))


def test_speed_and_cap_counted_from_rows():
    d = _embedded(report_html.render(ROWS))
    assert d["speed"]["C"]["hit_cap"] == 1 and d["speed"]["C"]["mean"] == 3.0
    assert d["speed"]["A2"]["n"] == 3


def test_template_placeholder_replaced_and_script_injection_safe():
    rows = ROWS + [_row("A2", "P1", "clean", 5, content="</script><b>oops</b>")]
    html = report_html.render(rows)
    assert "__DATA__" not in html
    # chuỗi </script> trong content không được làm đóng thẻ script sớm
    assert html.count("</script>") == 1
    assert _embedded(html)["rows"][-1]["content"] == "</script><b>oops</b>"


def test_config_info_comes_from_log_rows():
    d = _embedded(report_html.render(ROWS))
    assert d["cfgInfo"]["C"] == "m · GCD · think=off · num_predict=2048"


def test_hit_cap_uses_each_rows_own_num_predict_and_legacy_rows_default_to_2048():
    legacy = _row("B", "control", "truncated", 0, eval_count=2048)               # không có num_predict -> 2048
    four_k_full = {**_row("B4k", "control", "truncated", 0, eval_count=4096), "num_predict": 4096}
    four_k_ok = {**_row("B4k", "control", "clean", 1, eval_count=2048), "num_predict": 4096}  # 2048 < 4096: KHÔNG chạm trần
    d = _embedded(report_html.render([legacy, four_k_full, four_k_ok]))
    assert d["speed"]["B"]["hit_cap"] == 1
    assert d["speed"]["B4k"]["hit_cap"] == 1
    assert d["cfgInfo"]["B4k"].endswith("num_predict=4096")

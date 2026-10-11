import subprocess
import sys
from pathlib import Path

import archagent_config as cfg
from gcd_bench import docs, report, run

ARCHAGENT = Path(__file__).resolve().parents[2]


def test_default_paths_match_the_old_hardcoded_ones():
    assert cfg.PATHS.root == ARCHAGENT
    assert cfg.PATHS.sample_doc == ARCHAGENT / "data" / "sample_docs" / "fake_architecture_doc.md"
    assert cfg.PATHS.results("day01-02") == ARCHAGENT / "research" / "results" / "day01-02"
    assert cfg.PATHS.env_file == ARCHAGENT / ".env"


def test_sample_doc_actually_exists():
    assert cfg.PATHS.sample_doc.is_file()


def test_modules_use_the_central_config():
    assert docs.DOC_PATH == cfg.PATHS.sample_doc
    assert run.RUNS == cfg.PATHS.results("day01-02") / "runs.jsonl"
    assert report.RUNS == run.RUNS


def test_results_does_not_create_dir_unless_asked(tmp_path):
    p = cfg.Paths(root=tmp_path, data_dir=tmp_path / "d", results_dir=tmp_path / "r", env_file=tmp_path / ".env")
    assert not p.results("x").exists()
    assert p.results("x", create=True).is_dir()


def test_env_override_is_honoured(tmp_path):
    # chạy process riêng vì PATHS được tính lúc import
    code = "from archagent_config import PATHS; print(PATHS.results_dir); print(PATHS.data_dir)"
    env = {**__import__("os").environ, "ARCHAGENT_RESULTS_DIR": str(tmp_path / "R"), "ARCHAGENT_DATA_DIR": str(tmp_path / "D")}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, cwd=str(tmp_path))
    assert out.returncode == 0, out.stderr
    got = out.stdout.split()
    assert got == [str((tmp_path / "R").resolve()), str((tmp_path / "D").resolve())]

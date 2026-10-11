"""Nguồn duy nhất cho đường dẫn trong archagent. Mọi module import từ đây thay vì tự tính `Path(__file__).parents[n]`.

    from archagent_config import PATHS
    PATHS.sample_doc        # data/sample_docs/fake_architecture_doc.md
    PATHS.results("day01-02")  # research/results/day01-02 (tự tạo thư mục)

Ghi đè qua biến môi trường (tùy chọn, hữu ích khi test hoặc chạy trên máy khác):
    ARCHAGENT_DATA_DIR, ARCHAGENT_RESULTS_DIR, ARCHAGENT_ENV_FILE
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env_path(name: str, default: Path) -> Path:
    v = os.getenv(name)
    return Path(v).expanduser().resolve() if v else default


@dataclass(frozen=True)
class Paths:
    root: Path
    data_dir: Path
    results_dir: Path
    env_file: Path

    @property
    def sample_docs(self) -> Path:
        return self.data_dir / "sample_docs"

    @property
    def sample_doc(self) -> Path:
        return self.sample_docs / "fake_architecture_doc.md"

    @property
    def research(self) -> Path:
        return self.root / "research"

    @property
    def claude_dir(self) -> Path:
        """`.claude/` của workspace (tasks, notes, research), nằm cạnh thư mục archagent."""
        return self.root.parent / ".claude"

    @property
    def security_logs(self) -> Path:
        return self.root / "security" / "logs"

    def results(self, name: str, *, create: bool = False) -> Path:
        """Thư mục kết quả con, vd results('day01-02'). Chỉ tạo khi create=True để import không có tác dụng phụ."""
        p = self.results_dir / name
        if create:
            p.mkdir(parents=True, exist_ok=True)
        return p


PATHS = Paths(
    root=ROOT,
    data_dir=_env_path("ARCHAGENT_DATA_DIR", ROOT / "data"),
    results_dir=_env_path("ARCHAGENT_RESULTS_DIR", ROOT / "research" / "results"),
    env_file=_env_path("ARCHAGENT_ENV_FILE", ROOT / ".env"),
)

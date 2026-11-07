"""4. evaluate.py từ chối khi seed đánh giá chồng lên khoảng seed train."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import ROOT
from evaluate import check_eval_seeds


def test_check_eval_seeds_rejects_overlap():
    with pytest.raises(ValueError):
        check_eval_seeds(list(range(0, 5)), [0, 1, 2])
    with pytest.raises(ValueError):
        check_eval_seeds(list(range(8995, 9005)), [])
    with pytest.raises(ValueError):
        check_eval_seeds([9000, 9001], [9001])
    check_eval_seeds(list(range(9000, 9100)), [0, 1, 2])  # hợp lệ


def test_cli_refuses(run_dirs, tmp_path):
    if not run_dirs:
        pytest.skip("chưa có run nào trong results/")
    run = run_dirs[0]
    fake = tmp_path / run.name
    fake.mkdir()
    shutil.copy(run / "config.yaml", fake / "config.yaml")
    r = subprocess.run([sys.executable, str(ROOT / "evaluate.py"), "--run", str(fake), "--controller", "random", "--episodes", "2", "--seed0", "5"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", cwd=ROOT,
                       env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"})
    out = r.stdout or ""
    assert r.returncode == 2, out
    assert "TỪ CHỐI" in out, out
    assert not (fake / "eval").exists()

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"


def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return "nogit"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def make_run_id(phase: str, algo: str, seed: int) -> str:
    return f"{phase}_{algo}_s{seed}_{datetime.now().strftime('%Y%m%d-%H%M')}"


def physical_cores() -> int:
    try:
        import psutil  # type: ignore

        n = psutil.cpu_count(logical=False)
        if n:
            return int(n)
    except Exception:
        pass
    return max(1, (os.cpu_count() or 2) // 2)


def auto_n_envs() -> int:
    return max(1, physical_cores() - 1)

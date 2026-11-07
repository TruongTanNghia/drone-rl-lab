import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore", category=UserWarning)

from core.config import ExperimentCfg, load_config  # noqa: E402

PHASE_OF = {"smoke": "g0", "hover": "g1", "waypoint": "g2", "obstacle": "g3", "target": "g4"}


def make_cfg(task: str, **env_over) -> ExperimentCfg:
    """Config nhỏ cho test, dựa trên g0_smoke.yaml, đổi task và vài trường env."""
    base = load_config(ROOT / "configs" / "g0_smoke.yaml").model_dump(mode="json")
    base["phase"] = PHASE_OF[task]
    base["env"]["task"] = task
    base["env"]["hover"] = {}
    base["reward"] = {}
    base["env"]["randomization"] = {"wind_max": 1.0, "gust_sigma": 0.5, "gust_tau": 2.0, "mass_scale": [0.9, 1.1], "wind_cd": 0.02}
    base["env"]["episode_sec"] = 4
    base["env"]["speed_limit"] = 1.0
    base["env"].update(env_over)
    return ExperimentCfg.model_validate(base)


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def run_dirs(root) -> list[Path]:
    res = root / "results"
    return sorted(p for p in res.glob("g*_*") if (p / "config.yaml").exists())

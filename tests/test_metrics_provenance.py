"""5. Mỗi metrics.json có đủ trường nguồn gốc và config_hash khớp config.yaml trong thư mục run."""
import json

import pytest

from core.config import config_hash

REQUIRED = ("run_id", "config_hash", "git_commit", "eval_seeds", "n_episodes", "created_at", "metrics", "gate", "phase", "controller")


def _all_metrics(run_dirs):
    out = []
    for run in run_dirs:
        for mp in run.glob("eval/*/metrics.json"):
            out.append((run, mp))
    return out


def test_metrics_provenance(run_dirs):
    items = _all_metrics(run_dirs)
    if not items:
        pytest.skip("chưa có metrics.json nào")
    for run, mp in items:
        doc = json.loads(mp.read_text(encoding="utf-8"))
        for k in REQUIRED:
            assert k in doc, f"{mp} thiếu {k}"
        assert doc["schema"] == "drone-metrics/1"
        assert doc["run_id"] == run.name
        assert doc["config_hash"] == config_hash(run / "config.yaml"), f"{mp}: config_hash không khớp config.yaml"
        assert doc["n_episodes"] == len(doc["episodes"]) == doc["eval_seeds"][1] - doc["eval_seeds"][0] + 1
        assert doc["eval_seeds"][0] >= 9000
        # mỗi lượt phải có file quỹ đạo tương ứng
        for e in doc["episodes"]:
            assert (mp.parent / f"traj_{e['seed']}.json").exists(), f"thiếu traj_{e['seed']}.json"
        # và quỹ đạo phải đúng schema, cùng run_id
        tj = json.loads((mp.parent / f"traj_{doc['episodes'][0]['seed']}.json").read_text(encoding="utf-8"))
        assert tj["schema"] == "drone-traj/1" and tj["run_id"] == run.name
        for key in ("t", "p", "v", "rpy", "wp", "wind", "rays", "target", "bbox"):
            assert key in tj["frames"][0], key

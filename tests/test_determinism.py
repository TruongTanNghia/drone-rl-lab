"""2. Cùng seed + cùng controller → hai lần chạy cho quỹ đạo giống hệt (so mã băm)."""
import hashlib
import json

import pytest

from agents.controllers import make_controller
from conftest import make_cfg
from envs.registry import make_env
from evaluation.runner import run_episode


def _hash(traj):
    return hashlib.sha256(json.dumps(traj["frames"], sort_keys=True).encode()).hexdigest()


@pytest.mark.parametrize("task,ctrl", [("smoke", "random"), ("waypoint", "pid"), ("obstacle", "apf"), ("target", "bbox")])
def test_determinism(task, ctrl):
    cfg = make_cfg(task)
    env = make_env(cfg)
    try:
        c = make_controller(ctrl, env)
        s1, t1 = run_episode(env, c, 9100, "t")
        s2, t2 = run_episode(env, c, 9100, "t")
        assert _hash(t1) == _hash(t2)
        assert s1 == s2
        # seed khác phải cho quỹ đạo khác
        s3, t3 = run_episode(env, c, 9101, "t")
        assert _hash(t3) != _hash(t1)
    finally:
        env.close()


def test_determinism_across_instances():
    cfg = make_cfg("obstacle")
    hs = []
    for _ in range(2):
        env = make_env(cfg)
        c = make_controller("apf", env)
        _, t = run_episode(env, c, 9100, "t")
        env.close()
        hs.append(_hash(t))
    assert hs[0] == hs[1]

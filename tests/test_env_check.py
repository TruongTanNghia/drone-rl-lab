"""1. Mọi env qua stable_baselines3.common.env_checker.check_env."""
import pytest
from stable_baselines3.common.env_checker import check_env

from conftest import make_cfg
from envs.registry import make_env


@pytest.mark.parametrize("task", ["smoke", "hover", "waypoint", "obstacle", "target"])
def test_env_check(task):
    env = make_env(make_cfg(task))
    try:
        check_env(env, warn=True, skip_render_check=True)
        obs, info = env.reset(seed=1)
        assert obs.shape == env.observation_space.shape
        for k in ("t", "pos", "vel", "rpy", "goal", "events", "success", "crashed", "reason"):
            assert k in info, k
        assert env.SPEED_LIMIT == env.cfg.speed_limit and env.LIBRARY_SPEED_LIMIT == pytest.approx(0.25)
    finally:
        env.close()

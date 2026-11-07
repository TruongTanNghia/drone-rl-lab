"""Tạo env theo config."""
from __future__ import annotations

from typing import Any

from core.config import ExperimentCfg
from envs.base_task import BaseTask
from envs.hover import HoverTask, SmokeEnv
from envs.obstacle import ObstacleTask
from envs.target import TargetTask
from envs.waypoint import WaypointTask

TASKS: dict[str, type[BaseTask]] = {
    "smoke": SmokeEnv,
    "hover": HoverTask,
    "waypoint": WaypointTask,
    "obstacle": ObstacleTask,
    "target": TargetTask,
}


def make_env(cfg: ExperimentCfg, gui: bool = False, stage_overrides: dict[str, Any] | None = None, source: str | None = None, **kw) -> BaseTask:
    env_cfg = cfg.env
    if source is not None and env_cfg.task == "target":
        env_cfg = env_cfg.model_copy(deep=True)
        env_cfg.target.source = source  # type: ignore[union-attr]
    cls = TASKS[env_cfg.task]
    return cls(env_cfg, reward=cfg.reward, gui=gui, stage_overrides=stage_overrides, **kw)

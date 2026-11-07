"""Chạy N lượt đánh giá với một Controller, thu tóm tắt lượt và quỹ đạo."""
from __future__ import annotations

from typing import Callable

import numpy as np

from evaluation.trajectory import TrajectoryRecorder


def run_episode(env, controller, seed: int, run_id: str = "", record: bool = True, source: str | None = None) -> tuple[dict, dict | None]:
    controller.reset(seed)
    obs, info = env.reset(seed=seed)
    rec = TrajectoryRecorder(env, run_id, controller.name, seed, env.PHASE, source) if record else None
    if rec:
        rec.start(info)
    ret, steps = 0.0, 0
    done = False
    last_info = info
    while not done:
        a = controller.act(obs, info)
        obs, r, term, trunc, info = env.step(a)
        ret += r
        steps += 1
        if rec:
            rec.add(info, a, r)
        done = term or trunc
        last_info = info
    summary = {
        "seed": int(seed),
        "success": bool(last_info["success"]),
        "crashed": bool(last_info["crashed"]),
        "reason": last_info.get("reason", ""),
        "steps": steps,
        "t_end": float(last_info["t"]),
        "return": float(ret),
        "mass_scale": float(last_info.get("mass_scale", 1.0)),
        "stage": last_info.get("stage"),
    }
    for k in ("err_after_settle", "reached", "finish_t", "d_min_episode", "in_frame_frac", "visible_frac", "d_goal"):
        if k in last_info:
            summary[k] = last_info[k]
    traj = rec.finish(last_info) if rec else None
    return summary, traj


def run_eval(env, controller, seeds: list[int], run_id: str = "", on_episode: Callable[[int, dict, dict | None], None] | None = None, source: str | None = None) -> list[dict]:
    out = []
    for s in seeds:
        summary, traj = run_episode(env, controller, int(s), run_id, record=True, source=source)
        out.append(summary)
        if on_episode:
            on_episode(int(s), summary, traj)
    return out

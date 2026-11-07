"""Đo số bước mô phỏng mỗi giây (không render) với 1 env và với n env (SubprocVecEnv).

    python scripts/bench_env.py --config configs/g0_smoke.yaml --steps 3000
Ghi kết quả JSON vào docs/machine_bench.json để make_machine_md đọc.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import ExperimentCfg, load_config  # noqa: E402
from core.util import ROOT, auto_n_envs, now_iso, physical_cores  # noqa: E402


def _factory(cfg_dict: dict, rank: int):
    def _init():
        from envs.registry import make_env

        cfg = ExperimentCfg.model_validate(cfg_dict)
        env = make_env(cfg, gui=False)
        env.reset(seed=rank)
        return env

    return _init


def _action(rng, mode: str, n: int | None = None):
    shape = (4,) if n is None else (n, 4)
    if mode == "random":
        return rng.uniform(-1, 1, shape).astype(np.float32)
    return np.zeros(shape, dtype=np.float32)  # "hover": giữ yên, không reset


def bench_single(cfg: ExperimentCfg, steps: int, mode: str) -> tuple[float, int, float]:
    from envs.registry import make_env

    env = make_env(cfg, gui=False)
    env.reset(seed=0)
    rng = np.random.default_rng(0)
    n_reset, t_reset = 0, 0.0
    t0 = time.perf_counter()
    for _ in range(steps):
        _, _, term, trunc, _ = env.step(_action(rng, mode))
        if term or trunc:
            tr = time.perf_counter()
            env.reset()
            t_reset += time.perf_counter() - tr
            n_reset += 1
    dt = time.perf_counter() - t0
    env.close()
    return steps / dt, n_reset, (t_reset / n_reset * 1000 if n_reset else 0.0)


def bench_vec(cfg: ExperimentCfg, n_envs: int, steps_per_env: int, mode: str) -> float:
    from stable_baselines3.common.vec_env import SubprocVecEnv

    venv = SubprocVecEnv([_factory(cfg.model_dump(mode="json"), i) for i in range(n_envs)], start_method="spawn")
    venv.reset()
    rng = np.random.default_rng(0)
    t0 = time.perf_counter()
    for _ in range(steps_per_env):
        venv.step(_action(rng, mode, n_envs))
    dt = time.perf_counter() - t0
    venv.close()
    return steps_per_env * n_envs / dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/g0_smoke.yaml")
    ap.add_argument("--steps", type=int, default=3000)
    ap.add_argument("--n-envs", type=int, default=None)
    ap.add_argument("--out", default="docs/machine_bench.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    n_envs = args.n_envs or auto_n_envs()
    import psutil

    single_hover, _, _ = bench_single(cfg, args.steps, "hover")
    single_rand, n_reset, reset_ms = bench_single(cfg, args.steps, "random")
    vec_hover = bench_vec(cfg, n_envs, max(200, args.steps // n_envs), "hover")
    vec_rand = bench_vec(cfg, n_envs, max(200, args.steps // n_envs), "random")
    res = {
        "measured_at": now_iso(),
        "config": args.config,
        "task": cfg.env.task,
        "ctrl_freq": cfg.env.ctrl_freq,
        "pyb_freq": cfg.env.pyb_freq,
        "cpu": platform.processor(),
        "physical_cores": physical_cores(),
        "logical_cpus": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "steps_per_sec_1env_hover": round(single_hover, 1),
        "steps_per_sec_1env_random": round(single_rand, 1),
        "resets_in_random_run": n_reset,
        "reset_ms": round(reset_ms, 1),
        "n_envs": n_envs,
        "steps_per_sec_nenv_hover": round(vec_hover, 1),
        "steps_per_sec_nenv_random": round(vec_rand, 1),
    }
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

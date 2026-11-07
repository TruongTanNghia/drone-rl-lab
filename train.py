"""Huấn luyện PPO/SAC theo file YAML.

    python train.py --config configs/g1_hover.yaml --seed 0

Luôn gui=False. Tạo results/<run_id>/ với config.yaml, model.zip, vecnormalize.pkl, train_log.csv, tb/.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

from core.config import ExperimentCfg, dump_config, load_config
from core.util import RESULTS_DIR, auto_n_envs, git_commit, make_run_id, now_iso


def _env_factory(cfg_dict: dict, seed: int, rank: int, stage: dict | None):
    def _init():
        from stable_baselines3.common.monitor import Monitor

        from envs.registry import make_env

        cfg = ExperimentCfg.model_validate(cfg_dict)
        overrides = (stage or {}).get("overrides") or {}
        env = make_env(cfg, gui=False, stage_overrides=overrides)
        if stage:
            env.set_stage(stage["name"], overrides)
        env.reset(seed=seed + 1000 * rank)
        return Monitor(env, info_keywords=("success", "crashed"))

    return _init


class TrainLogger:
    """Ghi train_log.csv và curriculum theo rollout."""

    def __init__(self, run_dir: Path, cfg: ExperimentCfg):
        from stable_baselines3.common.callbacks import BaseCallback

        self.run_dir = run_dir
        self.cfg = cfg
        self.t0 = time.time()
        self.stage_idx = 0
        self.stages = cfg.env.curriculum
        self.recent: list[float] = []
        self.rows: list[dict] = []
        self.curriculum_log: list[dict] = []
        logger = self

        class _CB(BaseCallback):
            def __init__(self):
                super().__init__(verbose=0)
                self.last_ckpt = 0

            def _on_step(self) -> bool:
                for info in self.locals.get("infos", []):
                    ep = info.get("episode")
                    if ep is not None:
                        logger.recent.append(float(ep.get("success", 0.0)))
                logger._maybe_promote(self.model, self.num_timesteps)
                ce = logger.cfg.algo.checkpoint_every
                if ce and self.num_timesteps - self.last_ckpt >= ce:
                    self.last_ckpt = self.num_timesteps
                    ck = logger.run_dir / "checkpoints"
                    ck.mkdir(exist_ok=True)
                    self.model.save(str(ck / f"model_{self.num_timesteps}.zip"))
                    self.model.get_vec_normalize_env().save(str(ck / f"vecnormalize_{self.num_timesteps}.pkl"))
                return True

            def _on_rollout_end(self) -> None:
                logger._log_row(self.model, self.num_timesteps)

        self.callback = _CB()

    def _success_rate(self, window: int) -> float | None:
        if not self.recent:
            return None
        return float(np.mean(self.recent[-window:]))

    def _log_row(self, model, timesteps: int) -> None:
        buf = model.ep_info_buffer
        rew = float(np.mean([e["r"] for e in buf])) if len(buf) else None
        ln = float(np.mean([e["l"] for e in buf])) if len(buf) else None
        row = {
            "timesteps": int(timesteps),
            "ep_rew_mean": rew,
            "ep_len_mean": ln,
            "success_rate": self._success_rate(100),
            "wall_time": round(time.time() - self.t0, 1),
            "stage": self.stages[self.stage_idx].name if self.stages else "default",
        }
        self.rows.append(row)
        self.flush()

    def _maybe_promote(self, model, timesteps: int) -> None:
        if not self.stages or self.stage_idx >= len(self.stages) - 1:
            return
        st = self.stages[self.stage_idx]
        if st.promote_at is None or len(self.recent) < st.window:
            return
        sr = self._success_rate(st.window)
        if sr is not None and sr >= st.promote_at:
            self.stage_idx += 1
            nxt = self.stages[self.stage_idx]
            model.get_env().env_method("set_stage", nxt.name, nxt.overrides)
            self.recent = []
            ev = {"timesteps": int(timesteps), "from": st.name, "to": nxt.name, "success_rate": sr, "wall_time": round(time.time() - self.t0, 1)}
            self.curriculum_log.append(ev)
            print(f"[curriculum] t={timesteps}: {st.name} -> {nxt.name} (success_rate={sr:.3f})", flush=True)

    def flush(self) -> None:
        with open(self.run_dir / "train_log.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timesteps", "ep_rew_mean", "ep_len_mean", "success_rate", "wall_time", "stage"])
            w.writeheader()
            w.writerows(self.rows)
        if self.curriculum_log:
            with open(self.run_dir / "curriculum_log.json", "w", encoding="utf-8") as f:
                json.dump(self.curriculum_log, f, ensure_ascii=False, indent=2)


def train(cfg: ExperimentCfg, seed: int, run_id: str | None = None, results_dir: Path = RESULTS_DIR, n_envs_override: int | None = None) -> Path:
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

    from agents.model_factory import make_model

    if seed not in cfg.train_seeds:
        raise ValueError(f"seed {seed} không nằm trong train_seeds {cfg.train_seeds} của config")
    run_id = run_id or make_run_id(cfg.phase, cfg.algo.name, seed)
    run_dir = Path(results_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.yaml").write_text(dump_config(cfg), encoding="utf-8")

    n_envs = n_envs_override or (auto_n_envs() if cfg.algo.n_envs == "auto" else int(cfg.algo.n_envs))
    stage0 = None
    if cfg.env.curriculum:
        s = cfg.env.curriculum[0]
        stage0 = {"name": s.name, "overrides": s.overrides}
    cfg_dict = cfg.model_dump(mode="json")
    fns = [_env_factory(cfg_dict, seed, i, stage0) for i in range(n_envs)]
    venv = SubprocVecEnv(fns, start_method="spawn") if n_envs > 1 else DummyVecEnv(fns)
    venv = VecNormalize(venv, norm_obs=cfg.algo.vecnormalize.obs, norm_reward=cfg.algo.vecnormalize.reward, gamma=cfg.algo.gamma)
    venv.seed(seed)

    model = make_model(cfg, venv, seed, run_dir / "tb")
    logger = TrainLogger(run_dir, cfg)
    meta = {
        "run_id": run_id,
        "phase": cfg.phase,
        "algo": cfg.algo.name,
        "seed": seed,
        "n_envs": n_envs,
        "total_steps": cfg.algo.total_steps,
        "git_commit": git_commit(),
        "started_at": now_iso(),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    print(f"[train] {run_id}: {cfg.algo.name.upper()} n_envs={n_envs} total_steps={cfg.algo.total_steps} obs_dim={venv.observation_space.shape}", flush=True)
    t0 = time.time()
    model.learn(total_timesteps=cfg.algo.total_steps, callback=logger.callback, tb_log_name="run", progress_bar=False)
    wall = time.time() - t0
    model.save(str(run_dir / "model.zip"))
    venv.save(str(run_dir / "vecnormalize.pkl"))
    logger.flush()
    venv.close()
    meta.update({"finished_at": now_iso(), "wall_time_sec": round(wall, 1), "steps_per_sec": round(model.num_timesteps / wall, 1), "timesteps_done": int(model.num_timesteps)})
    with open(run_dir / "train_meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[train] xong {model.num_timesteps} bước trong {wall:.0f}s ({meta['steps_per_sec']} bước/s) -> {run_dir}", flush=True)
    return run_dir


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--n-envs", type=int, default=None, help="ghi đè số env (chỉ để thử nhanh)")
    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    train(cfg, args.seed, args.run_id, n_envs_override=args.n_envs)


if __name__ == "__main__":
    main()

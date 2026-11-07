"""Tạo model SB3 từ config."""
from __future__ import annotations

from pathlib import Path

from core.config import ExperimentCfg


def make_model(cfg: ExperimentCfg, vec_env, seed: int, tb_dir: str | Path):
    from stable_baselines3 import PPO, SAC

    a = cfg.algo
    pk = a.policy_kwargs
    if a.name == "ppo":
        policy_kwargs = {"net_arch": {"pi": list(pk.net_arch.pi), "vf": list(pk.net_arch.vf)}, "log_std_init": pk.log_std_init}
        return PPO(
            "MlpPolicy",
            vec_env,
            n_steps=a.n_steps,
            batch_size=a.batch_size,
            n_epochs=a.n_epochs,
            learning_rate=a.learning_rate,
            gamma=a.gamma,
            gae_lambda=a.gae_lambda,
            clip_range=a.clip_range,
            ent_coef=a.ent_coef,
            policy_kwargs=policy_kwargs,
            seed=seed,
            device="cpu",
            tensorboard_log=str(tb_dir),
            verbose=0,
        )
    if a.name == "sac":
        policy_kwargs = {"net_arch": {"pi": list(pk.net_arch.pi), "qf": list(pk.net_arch.qf)}, "log_std_init": pk.log_std_init}
        return SAC(
            "MlpPolicy",
            vec_env,
            learning_rate=a.learning_rate,
            gamma=a.gamma,
            batch_size=a.batch_size,
            policy_kwargs=policy_kwargs,
            seed=seed,
            device="cpu",
            tensorboard_log=str(tb_dir),
            verbose=0,
        )
    raise ValueError(a.name)

"""Đánh giá một controller trên N lượt, ghi metrics.json + traj_<seed>.json.

    python evaluate.py --run results/<run_id> --controller ppo --episodes 100
    python evaluate.py --run results/<run_id> --controller pid --episodes 100
    python evaluate.py --run results/<run_id> --controller ppo --source yolo --episodes 100   # G4

Từ chối chạy nếu seed đánh giá chồng lên khoảng seed train (0–8999) hoặc trùng train_seeds của run.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from core.config import EVAL_SEED_MIN, TRAIN_SEED_RANGE, config_hash, load_config
from core.util import git_commit, now_iso


def check_eval_seeds(seeds: list[int], train_seeds: list[int]) -> None:
    lo, hi = TRAIN_SEED_RANGE
    bad = [s for s in seeds if lo <= s <= hi or s < EVAL_SEED_MIN]
    if bad:
        raise ValueError(f"seed đánh giá {bad[:5]}... chồng lên khoảng seed train {TRAIN_SEED_RANGE} (eval phải ≥ {EVAL_SEED_MIN})")
    dup = sorted(set(seeds) & set(train_seeds))
    if dup:
        raise ValueError(f"seed đánh giá trùng train_seeds: {dup}")


def train_seed_from_run_id(run_id: str) -> int | None:
    m = re.search(r"_s(\d+)_", run_id)
    return int(m.group(1)) if m else None


def evaluate(run_dir: Path, controller_name: str, episodes: int, seed0: int | None, source: str | None, out_dir: Path | None = None, quiet: bool = False) -> dict:
    from agents.controllers import make_controller
    from envs.registry import make_env
    from evaluation.metrics import check_gate, compute_metrics
    from evaluation.runner import run_eval

    run_dir = Path(run_dir)
    cfg_path = run_dir / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"không thấy {cfg_path}")
    cfg = load_config(cfg_path)
    if seed0 is None:
        seed0 = cfg.eval.seed0
    seeds = list(range(seed0, seed0 + episodes))
    check_eval_seeds(seeds, cfg.train_seeds)

    if cfg.env.task != "target":
        source = None
    elif source is None:
        source = cfg.env.target.source
    env = make_env(cfg, gui=False, source=source)
    controller = make_controller(controller_name, env, run_dir=run_dir, cfg=cfg)
    tag = controller_name + (f"_{source}" if source else "")
    out_dir = Path(out_dir) if out_dir else run_dir / "eval" / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = run_dir.name
    t0 = time.time()

    def on_episode(seed, summary, traj):
        with open(out_dir / f"traj_{seed}.json", "w", encoding="utf-8") as f:
            json.dump(traj, f, ensure_ascii=False, separators=(",", ":"))
        if not quiet:
            print(f"  seed {seed}: success={summary['success']} crashed={summary['crashed']} reason='{summary['reason']}' steps={summary['steps']} return={summary['return']:.2f}", flush=True)

    eps = run_eval(env, controller, seeds, run_id, on_episode, source=source)
    env.close()
    metrics = compute_metrics(cfg.phase, eps, cfg.env.hover.success_err)
    gate = check_gate(cfg.gate, metrics)
    doc = {
        "schema": "drone-metrics/1",
        "run_id": run_id,
        "phase": cfg.phase,
        "controller": controller_name,
        "source": source,
        "train_seed": train_seed_from_run_id(run_id),
        "config_hash": config_hash(cfg_path),
        "git_commit": git_commit(),
        "created_at": now_iso(),
        "eval_seeds": [seeds[0], seeds[-1]],
        "n_episodes": len(seeds),
        "wall_time_sec": round(time.time() - t0, 2),
        "metrics": metrics,
        "gate": gate,
        "episodes": eps,
    }
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    if not quiet:
        print(json.dumps({k: metrics[k] for k in metrics}, ensure_ascii=False, indent=2))
        print(f"gate {gate['name']}: {gate['rule']} -> value={gate['value']} passed={gate['passed']}")
        print(f"ghi {out_dir / 'metrics.json'} ({len(seeds)} quỹ đạo, {doc['wall_time_sec']} s)")
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="results/<run_id>")
    ap.add_argument("--controller", default="ppo", choices=["ppo", "sac", "random", "pid", "apf", "bbox"])
    ap.add_argument("--episodes", type=int, default=None)
    ap.add_argument("--seed0", type=int, default=None)
    ap.add_argument("--source", default=None, choices=[None, "sim", "yolo"])
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    run_dir = Path(args.run)
    cfg = load_config(run_dir / "config.yaml")
    episodes = args.episodes if args.episodes is not None else cfg.eval.episodes
    try:
        evaluate(run_dir, args.controller, episodes, args.seed0, args.source, Path(args.out) if args.out else None)
    except ValueError as e:
        print(f"[TỪ CHỐI] {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()

"""Bay thử từng checkpoint của một run để xem lại quá trình huấn luyện (timeline).

    python scripts/eval_checkpoints.py --run results/<run_id> [--episodes 3] [--seed0 9000]

Với mỗi checkpoints/model_<N>.zip (+ vecnormalize_<N>.pkl) và model.zip cuối (nếu có): chạy `episodes` lượt
trên seed đánh giá (≥ 9000, không chồng seed train), ghi timeline/<N>/traj_<seed>.json + metrics.json,
và timeline/summary.json gồm metric từng mốc. Dashboard đọc summary này để tua qua các mốc trong viewer 3D.
Không làm thay evaluate.py (100 lượt, cổng nghiệm thu); đây chỉ là ảnh chụp policy theo thời gian.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.controllers import SB3Controller  # noqa: E402
from core.config import load_config  # noqa: E402
from core.util import git_commit, now_iso  # noqa: E402
from envs.registry import make_env  # noqa: E402
from evaluate import check_eval_seeds  # noqa: E402
from evaluation.metrics import compute_metrics  # noqa: E402
from evaluation.runner import run_eval  # noqa: E402

CK_RE = re.compile(r"^model_(\d+)\.zip$")


def list_checkpoints(run_dir: Path) -> list[tuple[int, Path, Path | None]]:
    out = []
    ck = run_dir / "checkpoints"
    if ck.exists():
        for p in ck.iterdir():
            m = CK_RE.match(p.name)
            if m:
                if time.time() - p.stat().st_mtime < 15:  # đang được train.py ghi dở
                    continue
                n = int(m.group(1))
                vn = ck / f"vecnormalize_{n}.pkl"
                out.append((n, p, vn if vn.exists() else None))
    out.sort()
    meta_p = run_dir / "train_meta.json"
    if (run_dir / "model.zip").exists() and meta_p.exists():
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        n = int(meta.get("timesteps_done", 0))
        if n and all(n != c[0] for c in out):
            vn = run_dir / "vecnormalize.pkl"
            out.append((n, run_dir / "model.zip", vn if vn.exists() else None))
    out.sort()
    return out


def eval_checkpoints(run_dir: Path, episodes: int, seed0: int | None, only_new: bool = True) -> dict:
    cfg = load_config(run_dir / "config.yaml")
    if seed0 is None:
        seed0 = cfg.eval.seed0
    seeds = list(range(seed0, seed0 + episodes))
    check_eval_seeds(seeds, cfg.train_seeds)
    source = cfg.env.target.source if cfg.env.task == "target" else None
    cks = list_checkpoints(run_dir)
    if not cks:
        raise SystemExit(f"{run_dir}: không có checkpoint nào (checkpoints/model_<N>.zip hoặc model.zip)")
    tl = run_dir / "timeline"
    tl.mkdir(exist_ok=True)
    sum_p = tl / "summary.json"
    prev = json.loads(sum_p.read_text(encoding="utf-8")) if sum_p.exists() else None
    done = {int(e["timesteps"]): e for e in (prev or {}).get("entries", [])} if prev and prev.get("n_episodes") == episodes and prev.get("seed0") == seed0 else {}

    env = make_env(cfg, gui=False, source=source)
    entries = []
    t0 = time.time()
    for n, mp, vn in cks:
        if only_new and n in done and (tl / str(n) / "metrics.json").exists():
            entries.append(done[n])
            continue
        ctrl = SB3Controller(run_dir, cfg.algo.name, model_path=mp, vecnorm_path=vn)
        out = tl / str(n)
        out.mkdir(exist_ok=True)

        def on_ep(seed, summary, traj, out=out):
            with open(out / f"traj_{seed}.json", "w", encoding="utf-8") as f:
                json.dump(traj, f, ensure_ascii=False, separators=(",", ":"))

        eps = run_eval(env, ctrl, seeds, run_dir.name, on_ep, source=source)
        metrics = compute_metrics(cfg.phase, eps, cfg.env.hover.success_err)
        doc = {"schema": "drone-metrics/1", "run_id": run_dir.name, "phase": cfg.phase, "controller": cfg.algo.name, "source": source,
               "checkpoint": str(mp.relative_to(run_dir)).replace("\\", "/"), "timesteps": n, "created_at": now_iso(), "git_commit": git_commit(),
               "eval_seeds": [seeds[0], seeds[-1]], "n_episodes": len(seeds), "metrics": metrics, "episodes": eps}
        with open(out / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        e = {"timesteps": n, "checkpoint": doc["checkpoint"], "metrics": metrics, "seeds": seeds,
             "episodes": [{k: ep[k] for k in ("seed", "success", "crashed", "reason", "steps", "return")} for ep in eps],
             "file": f"results/{run_dir.name}/timeline/{n}/metrics.json"}
        entries.append(e)
        print(f"  checkpoint {n:>9}: " + ", ".join(f"{k}={v}" for k, v in metrics.items() if v is not None and k in ("mean_pos_err_after_settle", "success_rate", "crash_count", "mean_return", "mean_reached", "in_frame_frac")), flush=True)
    env.close()
    summary = {"schema": "drone-timeline/1", "run_id": run_dir.name, "phase": cfg.phase, "controller": cfg.algo.name, "n_episodes": episodes,
               "seed0": seed0, "seeds": seeds, "created_at": now_iso(), "wall_time_sec": round(time.time() - t0, 1), "entries": entries}
    with open(sum_p, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"ghi {sum_p} ({len(entries)} mốc, {summary['wall_time_sec']} s)")
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--seed0", type=int, default=None)
    ap.add_argument("--all", action="store_true", help="chạy lại cả mốc đã có")
    a = ap.parse_args(argv)
    eval_checkpoints(Path(a.run), a.episodes, a.seed0, only_new=not a.all)


if __name__ == "__main__":
    main()

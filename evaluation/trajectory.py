"""Ghi quỹ đạo theo schema drone-traj/1 (mục 5.3)."""
from __future__ import annotations

import json
from pathlib import Path


def _r(x, nd=4):
    if x is None:
        return None
    if isinstance(x, (list, tuple)):
        return [_r(v, nd) for v in x]
    if isinstance(x, float):
        return round(x, nd)
    return x


class TrajectoryRecorder:
    def __init__(self, env, run_id: str, controller: str, seed: int, phase: str, source: str | None = None):
        self.doc = {
            "schema": "drone-traj/1",
            "phase": phase,
            "run_id": run_id,
            "controller": controller,
            "source": source,
            "seed": int(seed),
            "dt": round(env.CTRL_TIMESTEP, 6),
            "mass_scale": None,
            "world": None,
            "frames": [],
            "events": [],
            "outcome": {"success": False, "crashed": False, "reason": ""},
        }
        self.env = env

    def start(self, info: dict) -> None:
        self.doc["mass_scale"] = _r(float(info.get("mass_scale", 1.0)))
        self.doc["world"] = _r(self.env.world_description())
        self.add(info)

    def add(self, info: dict, action=None, reward: float | None = None) -> None:
        f = {
            "t": _r(float(info["t"])),
            "p": _r(info["pos"]),
            "v": _r(info["vel"]),
            "rpy": _r(info["rpy"]),
            "wp": info.get("wp"),
            "wind": _r(info.get("wind")),
            "rays": _r(info.get("rays"), 3),
            "target": _r(info.get("target")),
            "bbox": _r(info.get("bbox")),
            "a": _r([float(x) for x in action], 3) if action is not None else None,
            "r": _r(reward) if reward is not None else None,
        }
        self.doc["frames"].append(f)
        for ev in info.get("events", []):
            self.doc["events"].append(ev)

    def finish(self, info: dict) -> dict:
        self.doc["outcome"] = {"success": bool(info["success"]), "crashed": bool(info["crashed"]), "reason": info.get("reason", "")}
        # cập nhật world (vd. waypoint/obstacle được sinh trong reset; lấy lần cuối cho chắc)
        self.doc["world"] = _r(self.env.world_description())
        return self.doc

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.doc, f, ensure_ascii=False, separators=(",", ":"))
        return path

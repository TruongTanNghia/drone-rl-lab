"""Tính chỉ số theo giai đoạn từ danh sách tóm tắt lượt, và kiểm tra cổng."""
from __future__ import annotations

import operator

import numpy as np

OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}


def _mean(xs):
    xs = [float(x) for x in xs if x is not None]
    return float(np.mean(xs)) if xs else None


def _std(xs):
    xs = [float(x) for x in xs if x is not None]
    return float(np.std(xs)) if xs else None


def compute_metrics(phase: str, eps: list[dict], success_err: float = 0.1) -> dict:
    n = len(eps)
    crashed = [e for e in eps if e["crashed"]]
    m: dict = {
        "n_episodes": n,
        "mean_return": _mean([e["return"] for e in eps]),
        "std_return": _std([e["return"] for e in eps]),
        "mean_ep_len": _mean([e["steps"] for e in eps]),
        "crash_count": len(crashed),
        "truncation_count": sum(1 for e in eps if e["reason"] in ("out_of_bounds", "tilt")),
        "collision_count": sum(1 for e in eps if e["reason"] == "collision"),
    }
    if phase in ("g0", "g1"):
        errs = [e.get("err_after_settle") for e in eps if not e["crashed"]]
        m["mean_pos_err_after_settle"] = _mean(errs)
        m["std_pos_err_after_settle"] = _std(errs)
        m["max_pos_err_after_settle"] = max([float(x) for x in errs if x is not None], default=None)
        ok = [1.0 if (not e["crashed"] and e.get("err_after_settle") is not None and e["err_after_settle"] < success_err) else 0.0 for e in eps]
        m["success_rate"] = _mean(ok)
    elif phase == "g2":
        m["success_rate"] = _mean([1.0 if e["success"] else 0.0 for e in eps])
        m["mean_finish_time"] = _mean([e.get("finish_t") for e in eps if e["success"]])
        m["mean_reached"] = _mean([e.get("reached", 0) for e in eps])
    elif phase == "g3":
        m["success_rate"] = _mean([1.0 if (e["success"] and not e["crashed"]) else 0.0 for e in eps])
        m["mean_finish_time"] = _mean([e.get("finish_t") for e in eps if e["success"]])
        m["mean_min_clearance"] = _mean([e.get("d_min_episode") for e in eps])
    elif phase == "g4":
        m["in_frame_frac"] = _mean([e.get("in_frame_frac") for e in eps])
        m["std_in_frame_frac"] = _std([e.get("in_frame_frac") for e in eps])
        m["visible_frac"] = _mean([e.get("visible_frac") for e in eps])
        m["success_rate"] = _mean([1.0 if (not e["crashed"] and (e.get("in_frame_frac") or 0) >= 0.8) else 0.0 for e in eps])
        m["mean_final_offset"] = _mean([e.get("d_goal") for e in eps])
    return m


def check_gate(gate, metrics: dict) -> dict:
    v = metrics.get(gate.metric)
    passed = bool(v is not None and OPS[gate.op](v, gate.value))
    return {"name": gate.name, "rule": f"{gate.metric} {gate.op} {gate.value}", "value": v, "passed": passed, "extra": list(gate.extra)}

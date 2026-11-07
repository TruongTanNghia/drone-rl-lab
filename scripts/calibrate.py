"""Hiệu chỉnh hai thứ cần cho G1–G2 (ghi kết quả vào docs/library_notes.md):

1. Đáp ứng của VEL + DSLPIDControl theo speed_limit: ra lệnh bay ngang hết tốc trong 4 s,
   đo tốc độ đạt được và góc nghiêng lớn nhất → chọn speed_limit / max_tilt hợp lý.
2. Hệ số gió c_d: thả drone giữ vị trí (lệnh 0) dưới gió nền 2 m/s trong 6 s, đo độ trôi theo c_d.

    python scripts/calibrate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import ExperimentCfg, load_config  # noqa: E402
from envs.registry import make_env  # noqa: E402


def speed_response(base: ExperimentCfg, speed_limit: float, sec: float = 4.0) -> dict:
    d = base.model_dump(mode="json")
    d["env"]["task"] = "hover"
    d["phase"] = "g1"
    d["env"]["episode_sec"] = sec + 1
    d["env"]["speed_limit"] = speed_limit
    d["env"]["hover"] = {"goal": [0, 0, 1.5], "start_box": {"x": [0, 0], "y": [0, 0], "z": [1.5, 1.5]}, "bound_xy": 50, "bound_z": 10, "max_tilt": 3.0}
    cfg = ExperimentCfg.model_validate(d)
    env = make_env(cfg)
    env.reset(seed=0)
    vmax, tilt_max, zmin, zmax = 0.0, 0.0, 9.0, 0.0
    speeds = []
    crashed = False
    for k in range(int(sec * cfg.env.ctrl_freq)):
        _, _, term, trunc, info = env.step(np.array([1, 0, 0, 1], dtype=np.float32))
        v = float(np.hypot(info["vel"][0], info["vel"][1]))
        speeds.append(v)
        vmax = max(vmax, v)
        tilt_max = max(tilt_max, abs(info["rpy"][0]), abs(info["rpy"][1]))
        zmin, zmax = min(zmin, info["pos"][2]), max(zmax, info["pos"][2])
        if term:
            crashed = True
            break
    env.close()
    tail = speeds[-30:] if len(speeds) >= 30 else speeds
    return {"speed_limit": speed_limit, "v_max": round(vmax, 3), "v_steady": round(float(np.mean(tail)), 3), "tilt_max_rad": round(tilt_max, 3), "z_min": round(zmin, 2), "z_max": round(zmax, 2), "crashed": crashed}


def wind_drift(base: ExperimentCfg, cd: float, wind: float = 2.0, sec: float = 6.0) -> dict:
    d = base.model_dump(mode="json")
    d["env"]["task"] = "hover"
    d["phase"] = "g1"
    d["env"]["episode_sec"] = sec + 1
    d["env"]["speed_limit"] = 1.0
    d["env"]["hover"] = {"goal": [0, 0, 1.5], "start_box": {"x": [0, 0], "y": [0, 0], "z": [1.5, 1.5]}, "bound_xy": 50, "bound_z": 10, "max_tilt": 3.0}
    d["env"]["randomization"] = {"wind_max": wind, "gust_sigma": 0.0, "gust_tau": 2.0, "mass_scale": [1, 1], "wind_cd": cd}
    cfg = ExperimentCfg.model_validate(d)
    env = make_env(cfg)
    env.reset(seed=0)
    env.wind_base = np.array([wind, 0.0])  # cố định hướng +x, độ lớn = wind
    drift, vmax = 0.0, 0.0
    for _ in range(int(sec * cfg.env.ctrl_freq)):
        _, _, term, trunc, info = env.step(np.zeros(4, dtype=np.float32))  # lệnh "đứng yên": PID giữ vị trí hiện tại
        drift = float(np.hypot(info["pos"][0], info["pos"][1]))
        vmax = max(vmax, float(np.hypot(info["vel"][0], info["vel"][1])))
        if term:
            break
    env.close()
    return {"wind_cd": cd, "wind_mps": wind, "drift_m_after_6s": round(drift, 3), "v_max": round(vmax, 3), "force_at_rest_mN": round(cd * wind * 1000, 2), "weight_mN": round(0.027 * 9.8 * 1000, 1)}


def main():
    base = load_config("configs/g0_smoke.yaml")
    out = {"speed_response": [], "wind_drift": []}
    for sl in (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        r = speed_response(base, sl)
        out["speed_response"].append(r)
        print(r, flush=True)
    for cd in (0.005, 0.01, 0.02, 0.03, 0.05):
        r = wind_drift(base, cd)
        out["wind_drift"].append(r)
        print(r, flush=True)
    Path("docs/calibration.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

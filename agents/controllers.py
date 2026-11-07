"""Bộ điều khiển (giao diện 4.3).

    class Controller(Protocol):
        name: str
        def reset(self, seed: int) -> None: ...
        def act(self, obs: np.ndarray, info: dict) -> np.ndarray: ...

Mọi controller ra lệnh ActionType.VEL: [ux, uy, uz, speed_factor] với ‖u‖ bất kỳ (env chuẩn hóa) và speed_factor ∈ [0,1]
(env nhân với SPEED_LIMIT). Baseline chỉ đọc `info`, policy SB3 chỉ đọc `obs`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Controller(Protocol):
    name: str

    def reset(self, seed: int) -> None: ...

    def act(self, obs: np.ndarray, info: dict) -> np.ndarray: ...


def vel_action(v: np.ndarray, speed_limit: float) -> np.ndarray:
    """Vector vận tốc mong muốn (m/s) → hành động VEL 4 chiều."""
    v = np.asarray(v, dtype=np.float64)
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return np.zeros(4, dtype=np.float32)
    f = float(np.clip(n / speed_limit, 0.0, 1.0))
    return np.array([v[0] / n, v[1] / n, v[2] / n, f], dtype=np.float32)


class RandomController:
    name = "random"

    def __init__(self):
        self.rng = np.random.default_rng(0)

    def reset(self, seed: int) -> None:
        self.rng = np.random.default_rng(seed)

    def act(self, obs, info) -> np.ndarray:
        return self.rng.uniform(-1.0, 1.0, size=4).astype(np.float32)


class PIDBaseline:
    """VEL hướng về đích, hệ số tốc độ clip(k·d / speed_limit, 0, 1)."""

    name = "pid"

    def __init__(self, speed_limit: float, k: float = 1.0):
        self.speed_limit = float(speed_limit)
        self.k = float(k)

    def reset(self, seed: int) -> None:
        pass

    def act(self, obs, info) -> np.ndarray:
        d = np.asarray(info["goal"]) - np.asarray(info["pos"])
        return vel_action(self.k * d, self.speed_limit)


class APFBaseline:
    """Trường thế nhân tạo dùng đúng 16 tia của env.

    hút về đích tối đa v_att; tia có khoảng hở < d_rep sinh lực đẩy k_rep·(1/d − 1/d_rep)·(−hướng tia);
    thêm thành phần tiếp tuyến k_tan, giữ chiều vòng (hysteresis) tới khi thoát vùng vật cản.
    """

    name = "apf"

    def __init__(self, speed_limit: float, v_att: float = 1.5, d_rep: float = 1.0, k_rep: float = 0.4, k_tan: float = 0.6, k_z: float = 1.0, k_att: float = 1.0):
        self.speed_limit = float(speed_limit)
        self.v_att, self.d_rep, self.k_rep, self.k_tan, self.k_z, self.k_att = v_att, d_rep, k_rep, k_tan, k_z, k_att
        self.turn_sign = 0

    def reset(self, seed: int) -> None:
        self.turn_sign = 0

    def act(self, obs, info) -> np.ndarray:
        pos = np.asarray(info["pos"])
        goal = np.asarray(info["goal"])
        rays = np.asarray(info.get("rays") or [])
        dirs = np.asarray(info.get("ray_dirs") or [])
        to_goal = goal[:2] - pos[:2]
        dist = float(np.linalg.norm(to_goal))
        att = np.zeros(2) if dist < 1e-6 else to_goal / dist * min(self.v_att, self.k_att * dist)
        rep = np.zeros(2)
        if rays.size:
            close = rays < self.d_rep
            for d, u in zip(rays[close], dirs[close]):
                d = max(float(d), 0.05)
                rep -= u[:2] * self.k_rep * (1.0 / d - 1.0 / self.d_rep)
        tan = np.zeros(2)
        rn = float(np.linalg.norm(rep))
        if rn > 1e-6:
            if self.turn_sign == 0:
                # chọn chiều vòng theo phía có nhiều không gian hơn (so sánh hai tiếp tuyến với hướng đích)
                left = np.array([-rep[1], rep[0]])
                self.turn_sign = 1 if np.dot(left, att) >= 0 else -1
            tan = self.turn_sign * np.array([-rep[1], rep[0]]) / rn * self.k_tan
        else:
            self.turn_sign = 0
        v_xy = att + rep + tan
        vz = self.k_z * (goal[2] - pos[2])
        return vel_action(np.array([v_xy[0], v_xy[1], vz]), self.speed_limit)


class BBoxServoBaseline:
    """Từ tâm khung + độ cao → độ lệch mét → lệnh vận tốc về phía mục tiêu. Mất mục tiêu: lên thêm 1,5 m, giữ vị trí."""

    name = "bbox"

    def __init__(self, cam, fly_z: float, speed_limit: float, k_xy: float = 1.2, k_z: float = 1.0, climb: float = 1.5):
        self.cam = cam
        self.fly_z = float(fly_z)
        self.speed_limit = float(speed_limit)
        self.k_xy, self.k_z, self.climb = k_xy, k_z, climb

    def reset(self, seed: int) -> None:
        pass

    def act(self, obs, info) -> np.ndarray:
        b = info.get("bbox")
        z = float(info["pos"][2])
        if b is not None and b[0] > 0.5:
            off = self.cam.ground_offset_from_bbox(b[1], b[2], z)
            v_xy = self.k_xy * off
            vz = self.k_z * (self.fly_z - z)
        else:
            v_xy = np.zeros(2)
            vz = self.k_z * (self.fly_z + self.climb - z)
        return vel_action(np.array([v_xy[0], v_xy[1], vz]), self.speed_limit)


class SB3Controller:
    """Bọc policy SB3 (PPO/SAC) nạp từ thư mục run, kèm vecnormalize.pkl."""

    def __init__(self, run_dir: str | Path, algo: str = "ppo", deterministic: bool = True):
        import pickle

        from stable_baselines3 import PPO, SAC

        run_dir = Path(run_dir)
        self.name = algo
        self.deterministic = deterministic
        cls = {"ppo": PPO, "sac": SAC}[algo]
        self.model = cls.load(str(run_dir / "model.zip"), device="cpu")
        # Chuẩn hóa obs bằng thống kê trong vecnormalize.pkl (đọc trực tiếp, không cần env giả).
        self.obs_rms = None
        vn = run_dir / "vecnormalize.pkl"
        if vn.exists():
            with open(vn, "rb") as f:
                vnorm = pickle.load(f)
            if getattr(vnorm, "norm_obs", False) and vnorm.obs_rms is not None:
                self.obs_rms = vnorm.obs_rms
                self.clip_obs = float(vnorm.clip_obs)
                self.epsilon = float(vnorm.epsilon)

    def reset(self, seed: int) -> None:
        pass

    def act(self, obs, info) -> np.ndarray:
        o = np.asarray(obs, dtype=np.float32)
        if self.obs_rms is not None:
            o = np.clip((o - self.obs_rms.mean) / np.sqrt(self.obs_rms.var + self.epsilon), -self.clip_obs, self.clip_obs).astype(np.float32)
        a, _ = self.model.predict(o, deterministic=self.deterministic)
        return np.asarray(a, dtype=np.float32).reshape(4)


def make_controller(name: str, env, run_dir: str | Path | None = None, cfg=None):
    """name: random | pid | apf | bbox | ppo | sac"""
    if name == "random":
        return RandomController()
    if name == "pid":
        return PIDBaseline(env.SPEED_LIMIT)
    if name == "apf":
        return APFBaseline(env.SPEED_LIMIT)
    if name == "bbox":
        return BBoxServoBaseline(env.cam, env.cfg.target.fly_z, env.SPEED_LIMIT)
    if name in ("ppo", "sac"):
        if run_dir is None:
            raise ValueError("policy SB3 cần --run")
        return SB3Controller(run_dir, name)
    raise ValueError(f"controller lạ: {name}")

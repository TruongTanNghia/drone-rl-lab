"""Lớp nền cho mọi env của dự án (giao diện 4.1).

Kế thừa `BaseRLAviary` của gym-pybullet-drones, hành động `ActionType.VEL`
(3 giá trị hướng + 1 hệ số tốc độ, đi qua DSLPIDControl có sẵn).

Những gì lớp này thêm so với HoverAviary gốc:
  * ghi đè `_observationSpace` / `_computeObs` bằng `Encoder` (không dùng bộ đệm hành động),
  * `SPEED_LIMIT` lấy từ config thay cho 0.03·MAX_SPEED_KMH,
  * điểm xuất phát/đích/gió/khối lượng lấy từ `self.np_random` của Gymnasium (seed → lặp lại được),
  * gió nền + gió giật Ornstein–Uhlenbeck áp bằng `p.applyExternalForce(..., p.WORLD_FRAME)` mỗi bước PyBullet,
  * đổi khối lượng bằng `p.changeDynamics`,
  * phát hiện va chạm bằng `p.getContactPoints`,
  * `info` chuẩn: t, pos, vel, rpy, goal, events, success, crashed, reason (+ trường phụ theo giai đoạn),
  * curriculum: `set_stage(overrides)`.
"""
from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
import pybullet as p
from gymnasium import spaces

from gym_pybullet_drones.envs.BaseRLAviary import BaseRLAviary
from gym_pybullet_drones.utils.enums import ActionType, DroneModel, ObservationType, Physics

from core.config import EnvCfg
from perception.encoders import Encoder, StateEncoder


class BaseTask(BaseRLAviary):
    PHASE = "g0"

    def __init__(
        self,
        cfg: EnvCfg,
        reward: dict[str, float] | None = None,
        encoder: Encoder | None = None,
        gui: bool = False,
        record: bool = False,
        stage_overrides: dict[str, Any] | None = None,
    ):
        self.cfg = cfg
        self.rw = dict(self.default_reward())
        self.rw.update(reward or {})
        self.encoder: Encoder = encoder if encoder is not None else self.default_encoder()
        self.overrides: dict[str, Any] = dict(stage_overrides or {})
        self.stage_name = "default"

        # trạng thái lượt
        self.goal = np.zeros(3)
        self.events_all: list[dict] = []
        self.events_step: list[dict] = []
        self.success = False
        self.crashed = False
        self.reason = ""
        self.ctrl_step = 0
        self.mass_scale = 1.0
        self.wind_base = np.zeros(2)
        self.gust = np.zeros(2)
        self.wind_active = False
        self.obstacle_ids: list[int] = []
        self._pending_init = np.array([[0.0, 0.0, 1.0]])

        super().__init__(
            drone_model=DroneModel.CF2X,
            num_drones=1,
            initial_xyzs=self._pending_init.copy(),
            initial_rpys=np.zeros((1, 3)),
            physics=Physics.PYB,
            pyb_freq=cfg.pyb_freq,
            ctrl_freq=cfg.ctrl_freq,
            gui=gui,
            record=record,
            obs=ObservationType.KIN,
            act=ActionType.VEL,
        )
        # giá trị thư viện: 0.03 * MAX_SPEED_KMH * 1000/3600
        self.LIBRARY_SPEED_LIMIT = float(self.SPEED_LIMIT)
        self.SPEED_LIMIT = float(cfg.speed_limit)
        self.NOMINAL_MASS = float(self.M)
        self.EPISODE_LEN_SEC = float(cfg.episode_sec)
        self.max_ctrl_steps = int(round(self.EPISODE_LEN_SEC * self.CTRL_FREQ))

    # ------------------------------------------------------------------ hooks
    def default_reward(self) -> dict[str, float]:
        return {}

    def default_encoder(self) -> Encoder:
        return StateEncoder(self.cfg.obs_scales)

    def _ov(self, key: str, default):
        """Giá trị sau khi áp curriculum override."""
        v = self.overrides.get(key, None)
        return default if v is None else v

    def set_stage(self, name: str, overrides: dict[str, Any]) -> None:
        self.stage_name = name
        self.overrides = dict(overrides or {})

    def get_stage(self) -> str:
        return self.stage_name

    # ------------------------------------------------------------------ spaces
    def _actionSpace(self):
        # giữ nguyên 4 kênh VEL của thư viện, nhưng không tạo bộ đệm hành động
        return spaces.Box(low=-np.ones((1, 4), dtype=np.float32), high=np.ones((1, 4), dtype=np.float32), dtype=np.float32)

    def _observationSpace(self):
        return spaces.Box(low=-np.inf, high=np.inf, shape=(self.encoder.dim,), dtype=np.float32)

    def _preprocessAction(self, action):
        # BaseRLAviary thêm vào action_buffer; ta không dùng buffer nhưng giữ hành vi VEL
        self.action_buffer.append(action)
        return super()._preprocessAction(action)

    # ------------------------------------------------------------------ episode
    def _sample_episode(self) -> None:
        """Đặt self.INIT_XYZS, self.goal, gió, khối lượng... bằng self.np_random. Lớp con ghi đè."""
        raise NotImplementedError

    def _after_housekeeping(self) -> None:
        """Gọi sau khi PyBullet đã nạp mặt đất + drone: thêm vật thể, đổi khối lượng."""
        rz = self.cfg.randomization
        lo, hi = self._ov("mass_lo", rz.mass_scale[0]), self._ov("mass_hi", rz.mass_scale[1])
        self.mass_scale = float(self.np_random.uniform(lo, hi)) if hi > lo else float(lo)
        if abs(self.mass_scale - 1.0) > 1e-9:
            p.changeDynamics(int(self.DRONE_IDS[0]), -1, mass=self.NOMINAL_MASS * self.mass_scale, physicsClientId=self.CLIENT)

    def _sample_wind(self, wind_max: float, gust_sigma: float) -> None:
        self.wind_cd = float(self.cfg.randomization.wind_cd)
        self.gust_sigma = float(gust_sigma)
        self.gust_tau = float(self.cfg.randomization.gust_tau)
        self.gust = np.zeros(2)
        if wind_max > 0:
            mag = float(self.np_random.uniform(0.0, wind_max))
            ang = float(self.np_random.uniform(0.0, 2 * np.pi))
            self.wind_base = mag * np.array([np.cos(ang), np.sin(ang)])
        else:
            self.wind_base = np.zeros(2)
        self.wind_active = (wind_max > 0 or gust_sigma > 0) and self.wind_cd > 0

    def reset(self, seed: int | None = None, options: dict | None = None):
        gym.Env.reset(self, seed=seed)
        self.events_all = []
        self.events_step = []
        self.success = False
        self.crashed = False
        self.reason = ""
        self.ctrl_step = 0
        self.obstacle_ids = []
        self._sample_episode()
        self.INIT_XYZS = np.asarray(self._pending_init, dtype=np.float64).reshape(1, 3)
        p.resetSimulation(physicsClientId=self.CLIENT)
        self._housekeeping()
        self._after_housekeeping()
        for c in self.ctrl:
            c.reset()
        self._updateAndStoreKinematicInformation()
        self._startVideoRecording()
        self.last_clipped_action = np.zeros((1, 4))
        self._on_episode_start()
        obs = self._computeObs()
        info = self._computeInfo()
        return obs, info

    def _on_episode_start(self) -> None:
        pass

    def step(self, action):
        a = np.asarray(action, dtype=np.float32).reshape(1, 4)
        a = np.clip(a, -1.0, 1.0)
        self.events_step = []
        self.ctrl_step += 1
        self._pre_step()
        obs, reward, terminated, truncated, info = super().step(a)
        return obs, float(reward), bool(terminated), bool(truncated), info

    def _pre_step(self) -> None:
        pass

    # ------------------------------------------------------------------ physics + wind
    def _physics(self, rpm, nth_drone):
        super()._physics(rpm, nth_drone)
        if self.wind_active:
            self._apply_wind()

    def _apply_wind(self) -> None:
        dt = self.PYB_TIMESTEP
        if self.gust_sigma > 0:
            tau = max(self.gust_tau, 1e-3)
            noise = self.np_random.standard_normal(2)
            self.gust = self.gust + (-self.gust / tau) * dt + self.gust_sigma * np.sqrt(2.0 / tau) * np.sqrt(dt) * noise
        wind = self.wind_base + self.gust
        did = int(self.DRONE_IDS[0])
        pos, _ = p.getBasePositionAndOrientation(did, physicsClientId=self.CLIENT)
        vel, _ = p.getBaseVelocity(did, physicsClientId=self.CLIENT)
        f = self.wind_cd * (wind - np.asarray(vel[0:2]))
        p.applyExternalForce(did, -1, forceObj=[float(f[0]), float(f[1]), 0.0], posObj=list(pos), flags=p.WORLD_FRAME, physicsClientId=self.CLIENT)

    def current_wind(self) -> np.ndarray:
        return self.wind_base + self.gust

    # ------------------------------------------------------------------ sensing helpers
    def _contacts(self) -> list[int]:
        pts = p.getContactPoints(bodyA=int(self.DRONE_IDS[0]), physicsClientId=self.CLIENT)
        return sorted({int(c[2]) for c in pts})

    def _check_bounds(self, bound_xy: float, z_lo: float, z_hi: float, max_tilt: float) -> str:
        pos = self.pos[0]
        rpy = self.rpy[0]
        if abs(pos[0]) > bound_xy or abs(pos[1]) > bound_xy or pos[2] > z_hi or pos[2] < z_lo:
            return "out_of_bounds"
        if abs(rpy[0]) > max_tilt or abs(rpy[1]) > max_tilt:
            return "tilt"
        return ""

    def _event(self, kind: str, text: str) -> None:
        ev = {"t": round(self.t, 3), "kind": kind, "text": text}
        self.events_all.append(ev)
        self.events_step.append(ev)

    def _fail(self, reason: str, text: str) -> None:
        if not self.crashed and not self.success:
            self.crashed = True
            self.reason = reason
            self._event("bad", text)

    @property
    def t(self) -> float:
        return self.ctrl_step * self.CTRL_TIMESTEP

    # ------------------------------------------------------------------ obs / info
    def _raw(self) -> dict:
        return {
            "pos": self.pos[0].copy(),
            "vel": self.vel[0].copy(),
            "rpy": self.rpy[0].copy(),
            "ang_v": self.ang_v[0].copy(),
            "goal": self.goal.copy(),
        }

    def _update_task_state(self) -> None:
        """Cập nhật cờ success/crash, sự kiện... Gọi một lần mỗi bước, trước khi mã hóa quan sát."""
        raise NotImplementedError

    def _computeObs(self):
        self._update_task_state()
        self._last_raw = self._raw()
        return self.encoder.encode(self._last_raw)

    def _computeTerminated(self):
        return bool(self.success or self.crashed)

    def _computeTruncated(self):
        return bool(self.ctrl_step >= self.max_ctrl_steps) and not (self.success or self.crashed)

    def _base_info(self) -> dict:
        return {
            "t": round(self.t, 4),
            "pos": self.pos[0].tolist(),
            "vel": self.vel[0].tolist(),
            "rpy": self.rpy[0].tolist(),
            "ang_v": self.ang_v[0].tolist(),
            "goal": self.goal.tolist(),
            "events": list(self.events_step),
            "success": bool(self.success),
            "crashed": bool(self.crashed),
            "reason": self.reason,
            "mass_scale": float(self.mass_scale),
            "stage": self.stage_name,
            "wind": self.current_wind().tolist() if self.wind_active else None,
            "wp": None,
            "rays": None,
            "target": None,
            "bbox": None,
            "waypoints": [],
            "obstacles": [],
        }

    def _computeInfo(self):
        return self._base_info()

    # ------------------------------------------------------------------ world (cho viewer)
    def world_description(self) -> dict:
        """Mô tả thế giới cho file quỹ đạo (goal, waypoints, obstacles, arena)."""
        return {"goal": self.goal.tolist(), "waypoints": [], "obstacles": [], "arena": {"x": [-2, 2], "y": [-2, 2], "z_max": 2.5}}

"""G1 HoverTask và G0 SmokeEnv."""
from __future__ import annotations

import numpy as np

from envs.base_task import BaseTask


class HoverTask(BaseTask):
    """Giữ vị trí tại đích (mặc định (0,0,1)).

    Xuất phát ngẫu nhiên trên không trong `hover.start_box` (không xuất phát dưới đất).
    Reward: exp(-k·d) − c·‖v‖; bị cắt (ra ngoài vùng / nghiêng quá) thì `crash`.
    """

    PHASE = "g1"

    def default_reward(self) -> dict[str, float]:
        return {"dist_k": 2.0, "vel_pen": 0.05, "crash": -10.0}

    def _sample_episode(self) -> None:
        h = self.cfg.hover
        b = h.start_box
        start = np.array(
            [
                self.np_random.uniform(b.x[0], b.x[1]),
                self.np_random.uniform(b.y[0], b.y[1]),
                self.np_random.uniform(b.z[0], b.z[1]),
            ]
        )
        self._pending_init = start.reshape(1, 3)
        self.goal = np.array(h.goal, dtype=np.float64)
        rz = self.cfg.randomization
        self._sample_wind(self._ov("wind_max", rz.wind_max), self._ov("gust_sigma", rz.gust_sigma))
        self.err_sum = 0.0
        self.err_n = 0
        self.d = float(np.linalg.norm(self.goal - start))

    def _update_task_state(self) -> None:
        h = self.cfg.hover
        self.d = float(np.linalg.norm(self.goal - self.pos[0]))
        if self.ctrl_step == 0:
            return
        if self.t > h.settle_sec:
            self.err_sum += self.d
            self.err_n += 1
        why = self._check_bounds(h.bound_xy, -np.inf, h.bound_z, h.max_tilt)
        if why:
            self._fail(why, f"Cắt lượt: {why} tại t={self.t:.1f}s")
            return
        if self._contacts():
            self._fail("collision", f"Chạm đất/vật thể tại t={self.t:.1f}s")

    def _computeReward(self):
        if self.crashed:
            return float(self.rw["crash"])
        v = float(np.linalg.norm(self.vel[0]))
        return float(np.exp(-self.rw["dist_k"] * self.d) - self.rw["vel_pen"] * v)

    def _computeInfo(self):
        info = self._base_info()
        info["d_goal"] = self.d
        info["err_after_settle"] = (self.err_sum / self.err_n) if self.err_n else None
        return info

    def world_description(self) -> dict:
        h = self.cfg.hover
        return {
            "goal": self.goal.tolist(),
            "waypoints": [],
            "obstacles": [],
            "arena": {"x": [-h.bound_xy, h.bound_xy], "y": [-h.bound_xy, h.bound_xy], "z_max": h.bound_z},
        }


class SmokeEnv(HoverTask):
    """G0: bài toán của `HoverAviary` gốc (đích (0,0,1), reward max(0, 2 − d⁴), cắt lượt như HoverAviary)
    diễn đạt lại trên giao diện mục 4.1. Dùng để kiểm tra trọn vòng train → đánh giá → xem lại."""

    PHASE = "g0"

    def default_reward(self) -> dict[str, float]:
        return {"crash": 0.0}

    def _computeReward(self):
        if self.crashed:
            return float(self.rw["crash"])
        return float(max(0.0, 2.0 - self.d**4))

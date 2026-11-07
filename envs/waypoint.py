"""G2 WaypointTask: bay qua 4 điểm ngẫu nhiên, có gió và đổi khối lượng."""
from __future__ import annotations

import numpy as np

from envs.base_task import BaseTask
from perception.encoders import StateEncoder


class WaypointTask(BaseTask):
    PHASE = "g2"

    def default_reward(self) -> dict[str, float]:
        return {"progress": 5.0, "reach_bonus": 10.0, "time_penalty": 0.03, "crash": -50.0}

    def default_encoder(self):
        return StateEncoder(self.cfg.obs_scales, with_progress=True)

    def _sample_waypoints(self, n: int) -> np.ndarray:
        w = self.cfg.waypoints
        b = w.box
        start = np.array(w.start)
        pts: list[np.ndarray] = []
        tries = 0
        while len(pts) < n:
            tries += 1
            if tries > 5000:
                raise RuntimeError("không sinh được waypoint thỏa min_gap")
            c = np.array(
                [
                    self.np_random.uniform(b.x[0], b.x[1]),
                    self.np_random.uniform(b.y[0], b.y[1]),
                    self.np_random.uniform(b.z[0], b.z[1]),
                ]
            )
            prev = pts[-1] if pts else start
            if np.linalg.norm(c - prev) >= w.min_gap:
                pts.append(c)
        return np.array(pts)

    def _sample_episode(self) -> None:
        w = self.cfg.waypoints
        n = int(self._ov("waypoint_count", w.count))
        self.n_wp_total = w.count  # tiến độ luôn chia cho số điểm đầy đủ
        self._pending_init = np.array(w.start, dtype=np.float64).reshape(1, 3)
        self.waypoints = self._sample_waypoints(n)
        self.wp_idx = 0
        self.goal = self.waypoints[0].copy()
        rz = self.cfg.randomization
        self._sample_wind(self._ov("wind_max", rz.wind_max), self._ov("gust_sigma", rz.gust_sigma))
        self.prev_d = float(np.linalg.norm(self.goal - self._pending_init[0]))
        self.reached = 0
        self.finish_t = None
        self.step_reward_terms = {"progress": 0.0, "bonus": 0.0}

    def _update_task_state(self) -> None:
        w = self.cfg.waypoints
        self.step_reward_terms = {"progress": 0.0, "bonus": 0.0}
        d = float(np.linalg.norm(self.goal - self.pos[0]))
        if self.ctrl_step == 0:
            self.prev_d = d
            return
        self.step_reward_terms["progress"] = self.prev_d - d
        self.prev_d = d
        why = self._check_bounds(w.bound_xy, -np.inf, w.bound_z, w.max_tilt)
        if why:
            self._fail(why, f"Cắt lượt: {why} tại t={self.t:.1f}s")
            return
        if self._contacts():
            self._fail("collision", f"Chạm đất tại t={self.t:.1f}s")
            return
        if d < w.reach_radius:
            self.reached += 1
            self.step_reward_terms["bonus"] = 1.0
            self._event("good", f"Chạm điểm {self.reached}/{len(self.waypoints)}")
            if self.reached >= len(self.waypoints):
                self.success = True
                self.finish_t = self.t
                self.reason = ""
            else:
                self.wp_idx += 1
                self.goal = self.waypoints[self.wp_idx].copy()
                self.prev_d = float(np.linalg.norm(self.goal - self.pos[0]))

    def _computeReward(self):
        if self.crashed:
            return float(self.rw["crash"])
        r = self.rw["progress"] * self.step_reward_terms["progress"]
        r += self.rw["reach_bonus"] * self.step_reward_terms["bonus"]
        r -= self.rw["time_penalty"]
        return float(r)

    def _raw(self) -> dict:
        raw = super()._raw()
        raw["progress"] = self.reached / float(self.n_wp_total)
        return raw

    def _computeInfo(self):
        info = self._base_info()
        info["wp"] = int(self.wp_idx)
        info["reached"] = int(self.reached)
        info["finish_t"] = self.finish_t
        info["waypoints"] = self.waypoints.tolist()
        info["d_goal"] = float(np.linalg.norm(self.goal - self.pos[0]))
        return info

    def world_description(self) -> dict:
        w = self.cfg.waypoints
        return {
            "goal": self.waypoints[-1].tolist(),
            "waypoints": self.waypoints.tolist(),
            "obstacles": [],
            "arena": {"x": [-w.bound_xy, w.bound_xy], "y": [-w.bound_xy, w.bound_xy], "z_max": w.bound_z},
        }

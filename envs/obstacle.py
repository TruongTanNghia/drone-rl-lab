"""G3 ObstacleTask: né 9 cột trụ bằng 16 tia ngang (p.rayTestBatch)."""
from __future__ import annotations

from collections import deque

import numpy as np
import pybullet as p

from envs.base_task import BaseTask
from perception.encoders import StateEncoder


def push_vector_from_rays(rays: np.ndarray, dirs: np.ndarray, ray_len: float) -> np.ndarray:
    """Vector đẩy 2D: tổng các -hướng tia nhân (1 − d/L), chuẩn hóa về [-1,1]."""
    w = np.clip(1.0 - rays / ray_len, 0.0, 1.0)
    v = -(dirs[:, :2] * w[:, None]).sum(axis=0)
    n = np.linalg.norm(v)
    if n > 1.0:
        v = v / n
    return v


def bfs_path_exists(obstacles: list[tuple[float, float, float]], arena_x, arena_y, start, goal, radius: float, cell: float) -> bool:
    """Kiểm tra trên lưới có đường đi 2D từ start tới goal, drone coi như hình tròn bán kính `radius`."""
    xs = np.arange(arena_x[0], arena_x[1] + 1e-9, cell)
    ys = np.arange(arena_y[0], arena_y[1] + 1e-9, cell)
    nx, ny = len(xs), len(ys)
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    blocked = np.zeros((nx, ny), dtype=bool)
    for (ox, oy, r) in obstacles:
        blocked |= (gx - ox) ** 2 + (gy - oy) ** 2 < (r + radius) ** 2

    def idx(ptx, pty):
        return int(round((ptx - arena_x[0]) / cell)), int(round((pty - arena_y[0]) / cell))

    s = idx(start[0], start[1])
    g = idx(goal[0], goal[1])
    if blocked[s] or blocked[g]:
        return False
    seen = np.zeros_like(blocked)
    seen[s] = True
    q = deque([s])
    while q:
        cx, cy = q.popleft()
        if (cx, cy) == g:
            return True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx_, ny_ = cx + dx, cy + dy
            if 0 <= nx_ < nx and 0 <= ny_ < ny and not seen[nx_, ny_] and not blocked[nx_, ny_]:
                seen[nx_, ny_] = True
                q.append((nx_, ny_))
    return False


class ObstacleTask(BaseTask):
    PHASE = "g3"

    def default_reward(self) -> dict[str, float]:
        return {"progress": 5.0, "time_penalty": 0.03, "clearance_pen": 0.1, "goal_bonus": 50.0, "crash": -50.0}

    def default_encoder(self):
        o = self.cfg.obstacles
        return StateEncoder(self.cfg.obs_scales, n_rays=o.n_rays, push_vector=o.push_vector)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        o = self.cfg.obstacles
        ang = np.arange(o.n_rays) * 2 * np.pi / o.n_rays
        self.ray_dirs = np.stack([np.cos(ang), np.sin(ang), np.zeros_like(ang)], axis=1)
        self.rays = np.full(o.n_rays, o.ray_len)

    def _sample_map(self) -> list[tuple[float, float, float]]:
        o = self.cfg.obstacles
        n = int(self._ov("obstacle_count", o.count))
        for _attempt in range(200):
            cols: list[tuple[float, float, float]] = []
            tries = 0
            while len(cols) < n and tries < 2000:
                tries += 1
                r = float(self.np_random.uniform(o.radius[0], o.radius[1]))
                x = float(self.np_random.uniform(o.box.x[0], o.box.x[1]))
                y = float(self.np_random.uniform(o.box.y[0], o.box.y[1]))
                if all(np.hypot(x - cx, y - cy) >= r + cr + o.extra_gap for cx, cy, cr in cols):
                    cols.append((x, y, r))
            if len(cols) < n:
                continue
            if bfs_path_exists(cols, o.arena.x, o.arena.y, self._pending_init[0], self.goal, o.drone_radius, o.bfs_cell):
                return cols
        raise RuntimeError("không sinh được bản đồ có đường đi sau 200 lần")

    def _sample_episode(self) -> None:
        o = self.cfg.obstacles
        self._pending_init = np.array([[o.start_x, 0.0, o.fly_z]])
        self.goal = np.array([o.goal_x, float(self.np_random.uniform(o.goal_y[0], o.goal_y[1])), o.fly_z])
        self.columns = self._sample_map()
        ws = float(self._ov("wind_speed", o.wind_speed))
        rz = self.cfg.randomization
        self._sample_wind(ws, self._ov("gust_sigma", rz.gust_sigma))
        self.prev_d = float(np.linalg.norm(self.goal - self._pending_init[0]))
        self.d_min_episode = o.ray_len
        self.finish_t = None
        self.progress_term = 0.0

    def _after_housekeeping(self) -> None:
        super()._after_housekeeping()
        o = self.cfg.obstacles
        self.obstacle_ids = []
        for (x, y, r) in self.columns:
            col = p.createCollisionShape(p.GEOM_CYLINDER, radius=r, height=o.height, physicsClientId=self.CLIENT)
            vis = p.createVisualShape(p.GEOM_CYLINDER, radius=r, length=o.height, rgbaColor=[0.55, 0.6, 0.7, 1], physicsClientId=self.CLIENT)
            bid = p.createMultiBody(0, col, vis, basePosition=[x, y, o.height / 2], physicsClientId=self.CLIENT)
            self.obstacle_ids.append(int(bid))

    def _cast_rays(self) -> np.ndarray:
        o = self.cfg.obstacles
        pos = self.pos[0]
        froms = pos[None, :] + self.ray_dirs * o.ray_offset
        tos = pos[None, :] + self.ray_dirs * o.ray_len
        res = p.rayTestBatch(froms.tolist(), tos.tolist(), physicsClientId=self.CLIENT)
        span = o.ray_len - o.ray_offset
        d = np.array([o.ray_offset + r[2] * span if r[0] >= 0 else o.ray_len for r in res])
        return d

    def _update_task_state(self) -> None:
        o = self.cfg.obstacles
        self.rays = self._cast_rays()
        self.d_min = float(self.rays.min())
        self.d_min_episode = min(self.d_min_episode, self.d_min)
        d = float(np.linalg.norm(self.goal - self.pos[0]))
        if self.ctrl_step == 0:
            self.prev_d = d
            self.progress_term = 0.0
            return
        self.progress_term = self.prev_d - d
        self.prev_d = d
        a = o.arena
        why = ""
        pos = self.pos[0]
        if not (a.x[0] <= pos[0] <= a.x[1] and a.y[0] <= pos[1] <= a.y[1] and pos[2] <= a.z[1]):
            why = "out_of_bounds"
        elif abs(self.rpy[0][0]) > o.max_tilt or abs(self.rpy[0][1]) > o.max_tilt:
            why = "tilt"
        if why:
            self._fail(why, f"Cắt lượt: {why} tại t={self.t:.1f}s")
            return
        hit = self._contacts()
        if hit:
            what = "cột" if any(h in self.obstacle_ids for h in hit) else "đất"
            self._fail("collision", f"Va chạm {what} tại t={self.t:.1f}s")
            return
        dxy = float(np.linalg.norm(self.goal[:2] - pos[:2]))
        dz = abs(float(self.goal[2] - pos[2]))
        if dxy < o.goal_tol_xy and dz < o.goal_tol_z:
            self.success = True
            self.finish_t = self.t
            self._event("good", f"Tới đích tại t={self.t:.1f}s")

    def _computeReward(self):
        if self.crashed:
            return float(self.rw["crash"])
        o = self.cfg.obstacles
        r = self.rw["progress"] * self.progress_term - self.rw["time_penalty"]
        r -= self.rw["clearance_pen"] * max(0.0, o.clearance_pen_dist - self.d_min)
        if self.success:
            r += self.rw["goal_bonus"]
        return float(r)

    def _raw(self) -> dict:
        raw = super()._raw()
        o = self.cfg.obstacles
        raw["rays"] = self.rays.copy()
        raw["ray_len"] = o.ray_len
        if o.push_vector:
            raw["push"] = push_vector_from_rays(self.rays, self.ray_dirs, o.ray_len)
        return raw

    def _computeInfo(self):
        info = self._base_info()
        info["rays"] = [round(float(x), 3) for x in self.rays]
        info["ray_dirs"] = self.ray_dirs[:, :2].tolist()
        info["d_min"] = self.d_min
        info["d_min_episode"] = self.d_min_episode
        info["finish_t"] = self.finish_t
        info["obstacles"] = [{"x": x, "y": y, "r": r, "h": self.cfg.obstacles.height} for (x, y, r) in self.columns]
        info["d_goal"] = float(np.linalg.norm(self.goal - self.pos[0]))
        return info

    def world_description(self) -> dict:
        o = self.cfg.obstacles
        return {
            "goal": self.goal.tolist(),
            "waypoints": [],
            "obstacles": [{"x": x, "y": y, "r": r, "h": o.height} for (x, y, r) in self.columns],
            "arena": {"x": list(o.arena.x), "y": list(o.arena.y), "z_max": o.arena.z[1]},
        }

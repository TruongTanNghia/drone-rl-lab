"""G4 TargetTask: tìm và bám "người" (hình khối cao ~1,7 m) bằng camera nhìn xuống.

Vị trí thật của mục tiêu KHÔNG đi vào quan sát; chỉ dùng để tính reward và để nguồn `sim` chiếu ra khung.
"""
from __future__ import annotations

import numpy as np
import pybullet as p

from envs.base_task import BaseTask
from perception.bbox_sources import SimBBoxSource, YoloBBoxSource
from perception.camera import DownCamera
from perception.encoders import TargetEncoder

PERSON_RADIUS = 0.25


def build_person(client: int, height: float = 1.7, color=(0.85, 0.2, 0.2, 1.0)) -> int:
    """Người dựng từ hình khối: 2 chân, thân, đầu. Mass 0 (tĩnh), di chuyển bằng resetBasePositionAndOrientation."""
    leg_h = height * 0.45
    torso_h = height * 0.40
    head_r = height * 0.075
    torso_w = 0.22
    shapes = []
    # (type, dims, offset, color)
    shapes.append((p.GEOM_BOX, [0.06, 0.07, leg_h / 2], [0.0, 0.08, leg_h / 2], (0.15, 0.2, 0.5, 1)))
    shapes.append((p.GEOM_BOX, [0.06, 0.07, leg_h / 2], [0.0, -0.08, leg_h / 2], (0.15, 0.2, 0.5, 1)))
    shapes.append((p.GEOM_BOX, [0.09, torso_w, torso_h / 2], [0.0, 0.0, leg_h + torso_h / 2], color))
    shapes.append((p.GEOM_SPHERE, [head_r], [0.0, 0.0, leg_h + torso_h + head_r], (0.9, 0.75, 0.6, 1)))
    vis_ids = []
    for t, dims, off, col in shapes:
        if t == p.GEOM_BOX:
            vis_ids.append(p.createVisualShape(t, halfExtents=dims, rgbaColor=list(col), visualFramePosition=off, physicsClientId=client))
        else:
            vis_ids.append(p.createVisualShape(t, radius=dims[0], rgbaColor=list(col), visualFramePosition=off, physicsClientId=client))
    # một hình trụ bao làm collision (không va chạm với drone ở độ cao 4 m nhưng cần cho seg mask id duy nhất)
    col = p.createCollisionShape(p.GEOM_CYLINDER, radius=PERSON_RADIUS, height=height, collisionFramePosition=[0, 0, height / 2], physicsClientId=client)
    # ghép nhiều visual: tạo body gốc với visual đầu tiên, các phần còn lại là link cố định
    n = len(vis_ids)
    body = p.createMultiBody(
        baseMass=0,
        baseCollisionShapeIndex=col,
        baseVisualShapeIndex=vis_ids[0],
        basePosition=[0, 0, 0],
        linkMasses=[0.0] * (n - 1),
        linkCollisionShapeIndices=[-1] * (n - 1),
        linkVisualShapeIndices=vis_ids[1:],
        linkPositions=[[0, 0, 0]] * (n - 1),
        linkOrientations=[[0, 0, 0, 1]] * (n - 1),
        linkInertialFramePositions=[[0, 0, 0]] * (n - 1),
        linkInertialFrameOrientations=[[0, 0, 0, 1]] * (n - 1),
        linkParentIndices=[0] * (n - 1),
        linkJointTypes=[p.JOINT_FIXED] * (n - 1),
        linkJointAxis=[[0, 0, 1]] * (n - 1),
        physicsClientId=client,
    )
    return int(body)


class Walker:
    """Đi ngẫu nhiên tốc độ v, tự quay đầu khi ra ngoài bán kính R."""

    def __init__(self, rng: np.random.Generator, speed: float, radius: float, start: np.ndarray):
        self.rng = rng
        self.v = speed
        self.R = radius
        self.pos = np.array(start[:2], dtype=np.float64)
        self.heading = float(rng.uniform(0, 2 * np.pi))

    def step(self, dt: float) -> np.ndarray:
        self.heading += float(self.rng.normal(0.0, 0.35)) * dt
        if np.linalg.norm(self.pos) > self.R:
            back = np.arctan2(-self.pos[1], -self.pos[0])
            self.heading = back + float(self.rng.normal(0.0, 0.3))
        self.pos += self.v * dt * np.array([np.cos(self.heading), np.sin(self.heading)])
        return self.pos


class TargetTask(BaseTask):
    PHASE = "g4"

    def default_reward(self) -> dict[str, float]:
        return {"in_frame_base": 1.0, "center_k": 0.5, "lost": -0.5, "alt_pen": 0.1, "crash": -50.0}

    def default_encoder(self):
        return TargetEncoder(source=self.cfg.target.source, scales=self.cfg.obs_scales)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        tc = self.cfg.target
        self.cam = DownCamera(tc.img_w, tc.img_h, tc.cam_fov_deg)
        self.sim_source = SimBBoxSource(self.cam, tc.noise_sigma, tc.drop_prob, tc.edge_margin, PERSON_RADIUS, tc.height)
        self.yolo_source = None
        if tc.source == "yolo":
            self.yolo_source = YoloBBoxSource(self.cam, tc.yolo_model, conf=tc.yolo_conf, every=tc.yolo_every)
        self.source_name = tc.source
        self.person_id = -1
        self.bbox = {"vis": 0.0, "cx": 0.0, "cy": 0.0, "w": 0.0, "h": 0.0}
        self.true_in_frame = False

    def _sample_episode(self) -> None:
        tc = self.cfg.target
        start_t = np.array([self.np_random.uniform(-2, 2), self.np_random.uniform(-2, 2)])
        ang = self.np_random.uniform(0, 2 * np.pi)
        off = self.np_random.uniform(0, tc.start_offset)
        self._pending_init = np.array([[start_t[0] + off * np.cos(ang), start_t[1] + off * np.sin(ang), tc.fly_z]])
        speed = float(self.np_random.uniform(tc.speed[0], tc.speed[1]))
        self.walker = Walker(self.np_random, speed, tc.turn_radius, start_t)
        self.target_pos = np.array([start_t[0], start_t[1], 0.0])
        self.goal = self.target_pos.copy()
        rz = self.cfg.randomization
        self._sample_wind(self._ov("wind_max", rz.wind_max), self._ov("gust_sigma", rz.gust_sigma))
        self.in_frame_steps = 0
        self.visible_steps = 0

    def _after_housekeeping(self) -> None:
        super()._after_housekeeping()
        self.person_id = build_person(self.CLIENT, self.cfg.target.height)
        p.resetBasePositionAndOrientation(self.person_id, self.target_pos.tolist(), [0, 0, 0, 1], physicsClientId=self.CLIENT)
        self.obstacle_ids = [self.person_id]

    def _pre_step(self) -> None:
        xy = self.walker.step(self.CTRL_TIMESTEP)
        self.target_pos = np.array([xy[0], xy[1], 0.0])
        self.goal = self.target_pos.copy()
        yaw = self.walker.heading
        p.resetBasePositionAndOrientation(self.person_id, self.target_pos.tolist(), p.getQuaternionFromEuler([0, 0, yaw]), physicsClientId=self.CLIENT)

    def _update_task_state(self) -> None:
        tc = self.cfg.target
        pos = self.pos[0]
        if self.yolo_source is not None:
            self.bbox = self.yolo_source.get(self.np_random, pos, client=self.CLIENT, step=self.ctrl_step)
            # vẫn tính khung thật để tính reward / chỉ số
            self.sim_source.get(self.np_random, pos, self.target_pos)
        else:
            self.bbox = self.sim_source.get(self.np_random, pos, self.target_pos)
        tb = self.sim_source.last_true
        self.true_in_frame = bool(tb["vis"] > 0.5)
        if self.ctrl_step == 0:
            return
        self.in_frame_steps += int(self.true_in_frame)
        self.visible_steps += int(self.bbox["vis"] > 0.5)
        why = ""
        if abs(pos[0]) > tc.bound_xy or abs(pos[1]) > tc.bound_xy or pos[2] < tc.bound_z[0] or pos[2] > tc.bound_z[1]:
            why = "out_of_bounds"
        elif abs(self.rpy[0][0]) > tc.max_tilt or abs(self.rpy[0][1]) > tc.max_tilt:
            why = "tilt"
        if why:
            self._fail(why, f"Cắt lượt: {why} tại t={self.t:.1f}s")
            return
        if self._contacts():
            self._fail("collision", f"Va chạm tại t={self.t:.1f}s")

    def _computeReward(self):
        if self.crashed:
            return float(self.rw["crash"])
        tc = self.cfg.target
        tb = self.sim_source.last_true
        if self.true_in_frame:
            r = self.rw["in_frame_base"] - self.rw["center_k"] * (tb["cx"] ** 2 + tb["cy"] ** 2)
        else:
            r = self.rw["lost"]
        r -= self.rw["alt_pen"] * abs(float(self.pos[0][2]) - tc.fly_z)
        return float(r)

    def _raw(self) -> dict:
        raw = super()._raw()
        raw["bbox"] = dict(self.bbox)
        raw["z_ref"] = self.cfg.target.fly_z
        return raw

    def _computeInfo(self):
        info = self._base_info()
        info["target"] = self.target_pos.tolist()
        b = self.bbox
        info["bbox"] = [b["vis"], b["cx"], b["cy"], b["w"], b["h"]]
        info["true_in_frame"] = self.true_in_frame
        info["in_frame_frac"] = (self.in_frame_steps / self.ctrl_step) if self.ctrl_step else None
        info["visible_frac"] = (self.visible_steps / self.ctrl_step) if self.ctrl_step else None
        info["source"] = self.source_name
        info["altitude"] = float(self.pos[0][2])
        info["d_goal"] = float(np.linalg.norm(self.target_pos[:2] - self.pos[0][:2]))
        return info

    def last_camera_frame(self):
        if self.yolo_source is not None:
            return self.yolo_source.last_rgb
        return None

    def world_description(self) -> dict:
        tc = self.cfg.target
        return {
            "goal": self.target_pos.tolist(),
            "waypoints": [],
            "obstacles": [],
            "arena": {"x": [-tc.bound_xy, tc.bound_xy], "y": [-tc.bound_xy, tc.bound_xy], "z_max": tc.bound_z[1]},
            "camera": {"w": tc.img_w, "h": tc.img_h, "hfov_deg": tc.cam_fov_deg, "fly_z": tc.fly_z},
        }

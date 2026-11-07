"""Camera gimbal nhìn thẳng xuống + mô hình pinhole (G4).

Quy ước (khớp với p.getCameraImage):
  * mắt camera = vị trí drone − (0,0,eye_drop), nhìn theo −z, vector "lên" của ảnh = +x thế giới
    ⇒ hàng 0 của ảnh là phía +x (phía trước), cột 0 là phía +y (bên trái)   [right = forward × up = −y].
  * FOV *ngang* = cam_fov_deg (PyBullet nhận FOV dọc nên ta đổi: vfov = 2·atan(tan(hfov/2)·H/W)).
  * Khung chuẩn hóa: cx, cy ∈ [−1, 1], cx dương = bên phải ảnh (−y), cy dương = phía trên ảnh (+x);
    w, h = bề rộng/cao khung chia cho W, H.
"""
from __future__ import annotations

import math

import numpy as np
import pybullet as p

EYE_DROP = 0.05  # m, hạ mắt camera xuống dưới thân drone để không nhìn thấy chính nó
NEAR = 0.1
FAR = 50.0


class DownCamera:
    def __init__(self, width: int = 320, height: int = 240, hfov_deg: float = 70.0):
        self.W = int(width)
        self.H = int(height)
        self.hfov = math.radians(hfov_deg)
        self.tan_h = math.tan(self.hfov / 2)
        self.tan_v = self.tan_h * self.H / self.W
        self.vfov_deg = math.degrees(2 * math.atan(self.tan_v))
        self.proj = p.computeProjectionMatrixFOV(fov=self.vfov_deg, aspect=self.W / self.H, nearVal=NEAR, farVal=FAR)

    # ---------------------------------------------------------------- pinhole
    def eye(self, drone_pos: np.ndarray) -> np.ndarray:
        return np.asarray(drone_pos, dtype=np.float64) - np.array([0.0, 0.0, EYE_DROP])

    def project_point(self, pt: np.ndarray, drone_pos: np.ndarray) -> tuple[float, float, float]:
        """→ (cx, cy, depth) chuẩn hóa; depth ≤ 0 nghĩa là ở sau/ngang mắt."""
        rel = np.asarray(pt, dtype=np.float64) - self.eye(drone_pos)
        depth = -rel[2]
        if depth <= 1e-6:
            return 0.0, 0.0, depth
        cx = (-rel[1] / depth) / self.tan_h
        cy = (rel[0] / depth) / self.tan_v
        return float(cx), float(cy), float(depth)

    def project_box(self, center_xy: np.ndarray, radius: float, height: float, drone_pos: np.ndarray) -> dict:
        """Chiếu hộp bao của mục tiêu (hình trụ đứng bán kính r, cao h, chân ở z=0) → khung chuẩn hóa."""
        cx0, cy0 = float(center_xy[0]), float(center_xy[1])
        corners = []
        for dx in (-radius, radius):
            for dy in (-radius, radius):
                for z in (0.0, height):
                    corners.append(np.array([cx0 + dx, cy0 + dy, z]))
        xs, ys = [], []
        for c in corners:
            cx, cy, depth = self.project_point(c, drone_pos)
            if depth <= 1e-6:
                return {"vis": 0.0, "cx": 0.0, "cy": 0.0, "w": 0.0, "h": 0.0}
            xs.append(cx)
            ys.append(cy)
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        # giao với khung ảnh [-1,1]
        ix0, ix1, iy0, iy1 = max(x0, -1.0), min(x1, 1.0), max(y0, -1.0), min(y1, 1.0)
        if ix1 <= ix0 or iy1 <= iy0:
            return {"vis": 0.0, "cx": 0.0, "cy": 0.0, "w": 0.0, "h": 0.0}
        return {
            "vis": 1.0,
            "cx": (ix0 + ix1) / 2,
            "cy": (iy0 + iy1) / 2,
            "w": (ix1 - ix0) / 2,     # chia cho bề rộng ảnh chuẩn hóa (=2)
            "h": (iy1 - iy0) / 2,
        }

    def ground_offset_from_bbox(self, cx: float, cy: float, altitude: float) -> np.ndarray:
        """Ước lượng độ lệch (dx, dy) trên mặt đất theo mét từ tâm khung và độ cao (dùng cho BBoxServoBaseline)."""
        depth = max(altitude, 0.1)
        dx = cy * self.tan_v * depth
        dy = -cx * self.tan_h * depth
        return np.array([dx, dy])

    # ---------------------------------------------------------------- pybullet render
    def view_matrix(self, drone_pos: np.ndarray):
        e = self.eye(drone_pos)
        return p.computeViewMatrix(cameraEyePosition=e.tolist(), cameraTargetPosition=[e[0], e[1], e[2] - 1.0], cameraUpVector=[1, 0, 0])

    def render(self, drone_pos: np.ndarray, client: int, segmentation: bool = False):
        flags = p.ER_SEGMENTATION_MASK_OBJECT_AND_LINKINDEX if segmentation else p.ER_NO_SEGMENTATION_MASK
        w, h, rgb, dep, seg = p.getCameraImage(
            width=self.W,
            height=self.H,
            viewMatrix=self.view_matrix(drone_pos),
            projectionMatrix=self.proj,
            shadow=0,
            renderer=p.ER_TINY_RENDERER,
            flags=flags,
            physicsClientId=client,
        )
        rgb = np.reshape(np.asarray(rgb, dtype=np.uint8), (h, w, 4))[:, :, :3]
        seg = np.reshape(np.asarray(seg), (h, w)) if segmentation else None
        return rgb, seg

    def bbox_from_pixels(self, x0: float, y0: float, x1: float, y1: float) -> dict:
        """Khung pixel (gốc trên-trái) → khung chuẩn hóa."""
        cx = ((x0 + x1) / 2) / self.W * 2 - 1
        cy = 1 - ((y0 + y1) / 2) / self.H * 2
        return {"vis": 1.0, "cx": float(cx), "cy": float(cy), "w": float((x1 - x0) / self.W), "h": float((y1 - y0) / self.H)}

    def bbox_to_pixels(self, b: dict) -> tuple[float, float, float, float]:
        cxp = (b["cx"] + 1) / 2 * self.W
        cyp = (1 - b["cy"]) / 2 * self.H
        wp, hp = b["w"] * self.W, b["h"] * self.H
        return cxp - wp / 2, cyp - hp / 2, cxp + wp / 2, cyp + hp / 2

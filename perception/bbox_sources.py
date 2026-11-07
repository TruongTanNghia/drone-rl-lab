"""Hai nguồn khung mục tiêu cho G4, cùng trả dict {vis, cx, cy, w, h} (cùng thứ tự trường).

* `SimBBoxSource`: chiếu pinhole từ vị trí thật của mục tiêu, cộng nhiễu σ, bỏ ngẫu nhiên một tỉ lệ khung,
  mục tiêu sát mép ảnh coi như không thấy. Dùng khi train.
* `YoloBBoxSource`: render camera bằng p.getCameraImage (ER_TINY_RENDERER) mỗi N bước điều khiển và chạy YOLO ONNX.
"""
from __future__ import annotations

import numpy as np

from perception.camera import DownCamera

EMPTY = {"vis": 0.0, "cx": 0.0, "cy": 0.0, "w": 0.0, "h": 0.0}


class SimBBoxSource:
    name = "sim"

    def __init__(self, cam: DownCamera, noise_sigma: float, drop_prob: float, edge_margin: float, target_radius: float, target_height: float):
        self.cam = cam
        self.noise_sigma = noise_sigma
        self.drop_prob = drop_prob
        self.edge_margin = edge_margin
        self.r = target_radius
        self.h = target_height
        self.last_true: dict = dict(EMPTY)

    def get(self, rng: np.random.Generator, drone_pos: np.ndarray, target_pos: np.ndarray, **_) -> dict:
        b = self.cam.project_box(target_pos[:2], self.r, self.h, drone_pos)
        self.last_true = dict(b)
        if b["vis"] < 0.5:
            return dict(EMPTY)
        if abs(b["cx"]) > 1 - self.edge_margin or abs(b["cy"]) > 1 - self.edge_margin:
            return dict(EMPTY)
        if self.drop_prob > 0 and rng.uniform() < self.drop_prob:
            return dict(EMPTY)
        n = rng.normal(0.0, self.noise_sigma, size=4) if self.noise_sigma > 0 else np.zeros(4)
        return {
            "vis": 1.0,
            "cx": float(np.clip(b["cx"] + n[0], -1, 1)),
            "cy": float(np.clip(b["cy"] + n[1], -1, 1)),
            "w": float(max(0.0, b["w"] + n[2])),
            "h": float(max(0.0, b["h"] + n[3])),
        }


class YoloBBoxSource:
    name = "yolo"

    def __init__(self, cam: DownCamera, model_path: str, conf: float = 0.25, every: int = 2, target_cls: int = 0):
        from perception.yolo_onnx import YoloOnnx

        self.cam = cam
        self.yolo = YoloOnnx(model_path, conf=conf)
        self.every = max(1, int(every))
        self.target_cls = target_cls
        self.last: dict = dict(EMPTY)
        self.last_rgb: np.ndarray | None = None
        self.n_frames = 0

    def get(self, rng: np.random.Generator, drone_pos: np.ndarray, client: int, step: int, **_) -> dict:
        if step % self.every != 0 and self.last_rgb is not None:
            return dict(self.last)
        rgb, _ = self.cam.render(drone_pos, client)
        self.last_rgb = rgb
        self.n_frames += 1
        dets = [d for d in self.yolo.detect(rgb) if d[5] == self.target_cls]
        if not dets:
            self.last = dict(EMPTY)
        else:
            x0, y0, x1, y1, conf, _ = max(dets, key=lambda d: d[4])
            self.last = self.cam.bbox_from_pixels(x0, y0, x1, y1)
        return dict(self.last)

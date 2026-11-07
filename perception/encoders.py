"""Bộ mã hóa nhận thức (giao diện 4.2).

    class Encoder(Protocol):
        dim: int
        def encode(self, raw: dict) -> np.ndarray: ...

`raw` là dict do env cung cấp, các khóa chính:
    pos, vel, rpy, ang_v, goal        (np.ndarray 3)
    progress                          (float, G2)
    rays                              (np.ndarray n, mét; G3)
    ray_len                           (float)
    push                              (np.ndarray 2; G3 ablation)
    bbox                              (dict vis,cx,cy,w,h; G4, do nguồn sim/yolo tạo)
    z_ref                             (float, độ cao giữ ở G4)
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class Encoder(Protocol):
    dim: int

    def encode(self, raw: dict) -> np.ndarray: ...


class StateEncoder:
    """Quan sát trạng thái: (đích − vị trí), vận tốc, rpy, vận tốc góc, mỗi nhóm chia thang đo.

    Tùy chọn: thêm tiến độ (G2), tia (G3), vector đẩy (G3 ablation).
    """

    def __init__(
        self,
        scales: dict[str, float] | None = None,
        with_progress: bool = False,
        n_rays: int = 0,
        push_vector: bool = False,
    ):
        s = {"pos": 1.0, "vel": 1.0, "rpy": 1.0, "ang_v": 1.0}
        s.update(scales or {})
        self.scales = s
        self.with_progress = with_progress
        self.n_rays = int(n_rays)
        self.push_vector = push_vector
        self.dim = 12 + (1 if with_progress else 0) + self.n_rays + (2 if push_vector else 0)
        self.fields = ["goal-pos(3)", "vel(3)", "rpy(3)", "ang_v(3)"]
        if with_progress:
            self.fields.append("progress(1)")
        if self.n_rays:
            self.fields.append(f"1-d/ray_len({self.n_rays})")
        if push_vector:
            self.fields.append("push(2)")

    def encode(self, raw: dict) -> np.ndarray:
        parts = [
            (np.asarray(raw["goal"]) - np.asarray(raw["pos"])) / self.scales["pos"],
            np.asarray(raw["vel"]) / self.scales["vel"],
            np.asarray(raw["rpy"]) / self.scales["rpy"],
            np.asarray(raw["ang_v"]) / self.scales["ang_v"],
        ]
        if self.with_progress:
            parts.append(np.array([float(raw.get("progress", 0.0))]))
        if self.n_rays:
            rays = np.asarray(raw["rays"], dtype=np.float64)
            parts.append(1.0 - rays / float(raw["ray_len"]))
        if self.push_vector:
            parts.append(np.asarray(raw.get("push", np.zeros(2)), dtype=np.float64))
        out = np.concatenate(parts).astype(np.float32)
        assert out.shape == (self.dim,), out.shape
        return out


class TargetEncoder:
    """Quan sát G4 (15 chiều): vis, cx, cy, w, h, z − z_ref, vel(3), rpy(3), ang_v(3).

    `source` chỉ là nhãn để ghi vào metrics; env chọn nguồn khung (sim hay yolo) nhưng
    cả hai nguồn đều phải trả dict cùng 5 trường, cùng thứ tự, nên encoder này dùng chung.
    Ghi chú: prompt ghi "(14)" nhưng liệt kê 5+1+3+3+3 = 15 trường; ta giữ đủ 15.
    """

    FIELDS = ["vis", "cx", "cy", "w", "h", "z-z_ref", "vel(3)", "rpy(3)", "ang_v(3)"]

    def __init__(self, source: str = "sim", scales: dict[str, float] | None = None):
        assert source in ("sim", "yolo")
        self.source = source
        s = {"pos": 1.0, "vel": 1.0, "rpy": 1.0, "ang_v": 1.0}
        s.update(scales or {})
        self.scales = s
        self.dim = 15

    def encode(self, raw: dict) -> np.ndarray:
        b = raw["bbox"]
        out = np.concatenate(
            [
                np.array([b["vis"], b["cx"], b["cy"], b["w"], b["h"]], dtype=np.float64),
                np.array([(float(raw["pos"][2]) - float(raw["z_ref"])) / self.scales["pos"]]),
                np.asarray(raw["vel"]) / self.scales["vel"],
                np.asarray(raw["rpy"]) / self.scales["rpy"],
                np.asarray(raw["ang_v"]) / self.scales["ang_v"],
            ]
        ).astype(np.float32)
        assert out.shape == (self.dim,)
        return out

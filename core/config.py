"""Pydantic schema cho file YAML thí nghiệm.

Mọi khóa lạ đều bị từ chối (extra="forbid") để file sai khóa báo lỗi ngay.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoxCfg(_Strict):
    """Hộp giới hạn x, y, z dạng [min, max]."""
    x: list[float] = Field(min_length=2, max_length=2)
    y: list[float] = Field(min_length=2, max_length=2)
    z: list[float] = Field(min_length=2, max_length=2)


class HoverCfg(_Strict):
    goal: list[float] = Field(default=[0.0, 0.0, 1.0], min_length=3, max_length=3)
    start_box: BoxCfg = BoxCfg(x=[-0.8, 0.8], y=[-0.8, 0.8], z=[0.3, 1.7])
    bound_xy: float = 2.0
    bound_z: float = 2.5
    max_tilt: float = 0.8
    settle_sec: float = 3.0          # sai số vị trí tính sau giây này
    success_err: float = 0.1         # m


class WaypointCfg(_Strict):
    count: int = 4
    box: BoxCfg = BoxCfg(x=[-4, 4], y=[-4, 4], z=[1, 3])
    min_gap: float = 2.5
    reach_radius: float = 0.35
    start: list[float] = Field(default=[0.0, 0.0, 1.5], min_length=3, max_length=3)
    bound_xy: float = 6.0
    bound_z: float = 4.0
    max_tilt: float = 1.0


class ObstacleCfg(_Strict):
    count: int = 9
    radius: list[float] = Field(default=[0.3, 0.6], min_length=2, max_length=2)
    height: float = 4.0
    box: BoxCfg = BoxCfg(x=[-3.5, 3.5], y=[-4, 4], z=[0, 4])
    extra_gap: float = 1.1
    arena: BoxCfg = BoxCfg(x=[-7, 7], y=[-6, 6], z=[0, 4])
    start_x: float = -6.0
    goal_x: float = 6.0
    goal_y: list[float] = Field(default=[-2.0, 2.0], min_length=2, max_length=2)
    fly_z: float = 1.2
    goal_tol_xy: float = 0.5
    goal_tol_z: float = 0.6
    n_rays: int = 16
    ray_len: float = 4.0
    ray_offset: float = 0.12
    drone_radius: float = 0.25        # bán kính dùng cho BFS
    bfs_cell: float = 0.25
    clearance_pen_dist: float = 0.6
    push_vector: bool = False         # ablation: thêm 2 trường vector đẩy
    max_tilt: float = 1.0
    wind_speed: float = 0.5           # gió nhẹ cố định (m/s)


class TargetCfg(_Strict):
    height: float = 1.7
    speed: list[float] = Field(default=[1.0, 1.4], min_length=2, max_length=2)
    turn_radius: float = 9.0
    fly_z: float = 4.0
    cam_fov_deg: float = 70.0
    img_w: int = 320
    img_h: int = 240
    noise_sigma: float = 0.03
    drop_prob: float = 0.08
    edge_margin: float = 0.05         # tâm sát mép (|c| > 1 - margin) coi như không thấy
    source: Literal["sim", "yolo"] = "sim"
    yolo_every: int = 2               # render camera mỗi N bước điều khiển ở chế độ yolo
    yolo_model: str = "perception/weights/yolo_target.onnx"
    yolo_conf: float = 0.25
    bound_xy: float = 12.0
    bound_z: list[float] = Field(default=[0.5, 8.0], min_length=2, max_length=2)
    max_tilt: float = 1.0
    start_offset: float = 2.0         # drone xuất phát cách mục tiêu tối đa (m) theo phương ngang


class RandomizationCfg(_Strict):
    wind_max: float = 0.0
    gust_sigma: float = 0.0
    gust_tau: float = 2.0
    mass_scale: list[float] = Field(default=[1.0, 1.0], min_length=2, max_length=2)
    wind_cd: float = 0.0              # hệ số lực gió c_d (N·s/m), hiệu chỉnh ở G2, xem library_notes.md


class CurriculumStage(_Strict):
    name: str
    overrides: dict[str, float | int | None] = Field(default_factory=dict)
    promote_at: Optional[float] = None
    window: int = 100


class EnvCfg(_Strict):
    task: Literal["smoke", "hover", "waypoint", "obstacle", "target"]
    ctrl_freq: int = 30
    pyb_freq: int = 240
    episode_sec: float = 10.0
    speed_limit: float = 1.0
    obs_scales: dict[str, float] = Field(
        default_factory=lambda: {"pos": 1.0, "vel": 1.0, "rpy": 1.0, "ang_v": 1.0}
    )
    hover: HoverCfg = HoverCfg()
    waypoints: Optional[WaypointCfg] = None
    obstacles: Optional[ObstacleCfg] = None
    target: Optional[TargetCfg] = None
    randomization: RandomizationCfg = RandomizationCfg()
    curriculum: list[CurriculumStage] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self):
        if self.pyb_freq % self.ctrl_freq != 0:
            raise ValueError("pyb_freq phải chia hết cho ctrl_freq")
        if self.task == "waypoint" and self.waypoints is None:
            self.waypoints = WaypointCfg()
        if self.task == "obstacle" and self.obstacles is None:
            self.obstacles = ObstacleCfg()
        if self.task == "target" and self.target is None:
            self.target = TargetCfg()
        return self


class NetArch(_Strict):
    pi: list[int] = [64, 64]
    vf: list[int] = [64, 64]
    qf: list[int] = [256, 256]


class PolicyKwargs(_Strict):
    net_arch: NetArch = NetArch()
    log_std_init: float = -1.0


class VecNormCfg(_Strict):
    obs: bool = True
    reward: bool = True


class AlgoCfg(_Strict):
    name: Literal["ppo", "sac"] = "ppo"
    total_steps: int = 20_000
    n_envs: int | Literal["auto"] = "auto"
    n_steps: int = 1024
    batch_size: int = 256
    n_epochs: int = 10
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.0
    policy_kwargs: PolicyKwargs = PolicyKwargs()
    vecnormalize: VecNormCfg = VecNormCfg()
    checkpoint_every: int = 100_000


class EvalCfg(_Strict):
    episodes: int = 100
    seed0: int = 9000


class GateCfg(_Strict):
    name: str
    metric: str
    op: Literal[">=", "<=", ">", "<"]
    value: float
    extra: list[str] = Field(default_factory=list)  # điều kiện phụ (chữ), kiểm bằng make_report


class ExperimentCfg(_Strict):
    phase: Literal["g0", "g1", "g2", "g3", "g4"]
    env: EnvCfg
    reward: dict[str, float] = Field(default_factory=dict)
    algo: AlgoCfg = AlgoCfg()
    train_seeds: list[int] = [0]
    eval: EvalCfg = EvalCfg()
    gate: GateCfg

    @field_validator("train_seeds")
    @classmethod
    def _seeds(cls, v):
        for s in v:
            if not (TRAIN_SEED_RANGE[0] <= s <= TRAIN_SEED_RANGE[1]):
                raise ValueError(f"train seed {s} ngoài khoảng {TRAIN_SEED_RANGE}")
        return v


TRAIN_SEED_RANGE = (0, 8999)
EVAL_SEED_MIN = 9000


def load_config(path: str | Path) -> ExperimentCfg:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return ExperimentCfg.model_validate(raw)


def config_hash(path: str | Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_config(cfg: ExperimentCfg) -> str:
    return yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=False, allow_unicode=True)

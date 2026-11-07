"""Sinh dữ liệu ảnh YOLO từ mô phỏng (G4 phần B).

    python perception/make_dataset.py --n 4000 --out perception/data/sim_person

Mỗi cảnh (seed cảnh = chỉ số ảnh): độ cao 2–8 m, mục tiêu ở vị trí ngẫu nhiên (85 % ảnh có mục tiêu),
màu + vân mặt đất ngẫu nhiên (texture sinh bằng numpy, nạp bằng p.loadTexture), 0–6 vật gây nhiễu (hộp/trụ màu ngẫu nhiên).
Nhãn lấy tự động từ ảnh segmentation của p.getCameraImage (id của mục tiêu), ghi theo định dạng YOLO.
Chia train/val/test THEO SEED CẢNH: seed % 10 == 0 → test, == 1 → val, còn lại → train (không rò rỉ).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pybullet as p
import pybullet_data
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from envs.target import PERSON_RADIUS, build_person  # noqa: E402
from perception.camera import DownCamera  # noqa: E402

SEG_OBJ_MASK = (1 << 24) - 1


def make_texture(rng: np.random.Generator, path: Path, size: int = 256) -> Path:
    """Vân mặt đất: nhiễu nhiều tầng + màu nền ngẫu nhiên (đất, cỏ, bê tông, cát...)."""
    base = rng.uniform(0.15, 0.85, 3)
    tint = rng.uniform(-0.25, 0.25, 3)
    img = np.zeros((size, size, 3))
    for scale in (4, 16, 64):
        n = rng.uniform(-1, 1, (scale, scale))
        up = np.kron(n, np.ones((size // scale, size // scale)))
        img += up[:, :, None] * (1.0 / scale ** 0.5) * tint[None, None, :] * 2
    kind = rng.integers(0, 3)
    if kind == 1:  # ô gạch
        yy, xx = np.mgrid[0:size, 0:size]
        tiles = (((xx // 32) + (yy // 32)) % 2) * 0.08
        img += tiles[:, :, None]
    elif kind == 2:  # vạch kẻ
        yy = np.arange(size)[:, None]
        img += (np.sin(yy / 9.0) > 0.9)[:, :, None] * 0.25
    img = np.clip(base[None, None, :] + img, 0, 1)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)
    return path


def split_of(seed: int) -> str:
    r = seed % 10
    return "test" if r == 0 else ("val" if r == 1 else "train")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--out", default="perception/data/sim_person")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--w", type=int, default=320)
    ap.add_argument("--h", type=int, default=240)
    ap.add_argument("--fov", type=float, default=70.0)
    ap.add_argument("--target-prob", type=float, default=0.85)
    args = ap.parse_args()

    out = Path(args.out)
    for sp in ("train", "val", "test"):
        (out / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sp).mkdir(parents=True, exist_ok=True)
    tex_dir = out / "_textures"
    tex_dir.mkdir(exist_ok=True)

    client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
    cam = DownCamera(args.w, args.h, args.fov)
    counts = {"train": 0, "val": 0, "test": 0}
    with_target = 0
    t0 = time.time()
    for i in range(args.start, args.start + args.n):
        rng = np.random.default_rng(i)
        p.resetSimulation(physicsClientId=client)
        plane = p.loadURDF("plane.urdf", physicsClientId=client)
        tex = p.loadTexture(str(make_texture(rng, tex_dir / f"tex_{i % 64}.png")), physicsClientId=client)
        p.changeVisualShape(plane, -1, textureUniqueId=tex, rgbaColor=[*rng.uniform(0.5, 1.0, 3), 1], physicsClientId=client)
        alt = float(rng.uniform(2.0, 8.0))
        drone_pos = np.array([rng.uniform(-3, 3), rng.uniform(-3, 3), alt])
        # vật gây nhiễu
        for _ in range(int(rng.integers(0, 7))):
            kind = rng.integers(0, 2)
            col = [*rng.uniform(0.1, 1.0, 3), 1]
            ox, oy = drone_pos[0] + rng.uniform(-alt, alt), drone_pos[1] + rng.uniform(-alt * 0.75, alt * 0.75)
            if kind == 0:
                he = rng.uniform(0.1, 0.6, 3)
                vs = p.createVisualShape(p.GEOM_BOX, halfExtents=he.tolist(), rgbaColor=col, physicsClientId=client)
                p.createMultiBody(0, -1, vs, basePosition=[ox, oy, he[2]], baseOrientation=p.getQuaternionFromEuler([0, 0, rng.uniform(0, 3.14)]), physicsClientId=client)
            else:
                r, h = rng.uniform(0.1, 0.5), rng.uniform(0.2, 1.5)
                vs = p.createVisualShape(p.GEOM_CYLINDER, radius=r, length=h, rgbaColor=col, physicsClientId=client)
                p.createMultiBody(0, -1, vs, basePosition=[ox, oy, h / 2], physicsClientId=client)
        has_target = rng.uniform() < args.target_prob
        pid = -1
        if has_target:
            pid = build_person(client, height=float(rng.uniform(1.55, 1.85)), color=(*rng.uniform(0.1, 1.0, 3), 1.0))
            half_x = np.tan(np.radians(args.fov / 2)) * alt * args.h / args.w
            half_y = np.tan(np.radians(args.fov / 2)) * alt
            tx = drone_pos[0] + rng.uniform(-half_x * 1.05, half_x * 1.05)
            ty = drone_pos[1] + rng.uniform(-half_y * 1.05, half_y * 1.05)
            p.resetBasePositionAndOrientation(pid, [tx, ty, 0], p.getQuaternionFromEuler([0, 0, rng.uniform(0, 6.28)]), physicsClientId=client)
        rgb, seg = cam.render(drone_pos, client, segmentation=True)
        sp = split_of(i)
        name = f"{i:06d}"
        Image.fromarray(rgb).save(out / "images" / sp / f"{name}.jpg", quality=92)
        lines = []
        if has_target:
            mask = (seg & SEG_OBJ_MASK) == pid
            if mask.sum() >= 6:
                ys, xs = np.where(mask)
                x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
                lines.append(f"0 {((x0 + x1) / 2) / args.w:.6f} {((y0 + y1) / 2) / args.h:.6f} {(x1 - x0) / args.w:.6f} {(y1 - y0) / args.h:.6f}")
                with_target += 1
        (out / "labels" / sp / f"{name}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        counts[sp] += 1
        if (i - args.start + 1) % 200 == 0:
            print(f"{i - args.start + 1}/{args.n} ảnh, {time.time() - t0:.0f}s", flush=True)
    p.disconnect(client)
    (out / "data.yaml").write_text(f"path: {out.resolve().as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: person\n", encoding="utf-8")
    meta = {"n": args.n, "start": args.start, "counts": counts, "images_with_target_box": with_target, "img": [args.w, args.h], "hfov_deg": args.fov, "split_rule": "seed%10: 0=test, 1=val, else train", "seconds": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()

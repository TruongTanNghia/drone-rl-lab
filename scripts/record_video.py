"""Ghép khung hình từ p.getCameraImage (chế độ DIRECT) thành video bằng ffmpeg — mỗi giai đoạn một video (G5).

    python scripts/record_video.py --traj results/<run>/eval/ppo/traj_9000.json --out results/videos/g1.mp4
    python scripts/record_video.py --phase g1            # tự chọn run mới nhất của g1, quỹ đạo thành công đầu tiên của policy

Phát lại quỹ đạo (không chạy vật lý): nạp plane + cf2x.urdf, đặt pose drone theo từng khung bằng resetBasePositionAndOrientation,
dựng lại cột/waypoint/mục tiêu từ `world`, quay bằng camera đuổi theo drone. Với G4 ghép thêm ảnh camera nhìn xuống + khung YOLO/sim.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from importlib.resources import files
from pathlib import Path

import numpy as np
import pybullet as p
import pybullet_data

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.util import ROOT  # noqa: E402
from envs.target import build_person  # noqa: E402
from perception.camera import DownCamera  # noqa: E402


def pick_traj(phase: str) -> Path:
    runs = sorted((ROOT / "results").glob(f"{phase}_*"))
    if not runs:
        raise SystemExit(f"chưa có run nào của {phase}")
    for run in reversed(runs):
        for tag in ("ppo", "ppo_sim", "ppo_yolo", "sac"):
            mp = run / "eval" / tag / "metrics.json"
            if mp.exists():
                doc = json.loads(mp.read_text(encoding="utf-8"))
                ok = [e for e in doc["episodes"] if e["success"] and not e["crashed"]] or doc["episodes"]
                return mp.parent / f"traj_{ok[0]['seed']}.json"
    raise SystemExit(f"{phase}: chưa có đánh giá policy nào")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traj", default=None)
    ap.add_argument("--phase", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--w", type=int, default=960)
    ap.add_argument("--h", type=int, default=540)
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()
    traj_path = Path(args.traj) if args.traj else pick_traj(args.phase)
    doc = json.loads(traj_path.read_text(encoding="utf-8"))
    out = Path(args.out) if args.out else ROOT / "results" / "videos" / f"{doc['phase']}_{doc['controller']}_{doc['seed']}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=client)
    p.loadURDF("plane.urdf", physicsClientId=client)
    drone = p.loadURDF(str(files("gym_pybullet_drones") / "assets" / "cf2x.urdf"), [0, 0, 1], physicsClientId=client, globalScaling=3.0)
    world = doc.get("world") or {}
    for o in world.get("obstacles") or []:
        vs = p.createVisualShape(p.GEOM_CYLINDER, radius=o["r"], length=o.get("h", 4), rgbaColor=[0.55, 0.6, 0.7, 1], physicsClientId=client)
        p.createMultiBody(0, -1, vs, basePosition=[o["x"], o["y"], o.get("h", 4) / 2], physicsClientId=client)
    for w in world.get("waypoints") or []:
        vs = p.createVisualShape(p.GEOM_SPHERE, radius=0.18, rgbaColor=[0.98, 0.75, 0.14, 1], physicsClientId=client)
        p.createMultiBody(0, -1, vs, basePosition=w, physicsClientId=client)
    if world.get("goal") and not world.get("waypoints"):
        vs = p.createVisualShape(p.GEOM_SPHERE, radius=0.15, rgbaColor=[0.2, 0.83, 0.6, 1], physicsClientId=client)
        p.createMultiBody(0, -1, vs, basePosition=world["goal"], physicsClientId=client)
    person = None
    if any(f.get("target") for f in doc["frames"]):
        person = build_person(client)
    cam_down = DownCamera(320, 240, (world.get("camera") or {}).get("hfov_deg", 70.0)) if any(f.get("bbox") for f in doc["frames"]) else None

    proj = p.computeProjectionMatrixFOV(fov=50, aspect=args.w / args.h, nearVal=0.05, farVal=200)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{args.w}x{args.h}", "-r", str(args.fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(out)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    step = max(1, int(round((1.0 / args.fps) / doc["dt"])))
    frames = doc["frames"][::step]
    for f in frames:
        pos = f["p"]
        quat = p.getQuaternionFromEuler(f["rpy"])
        p.resetBasePositionAndOrientation(drone, pos, quat, physicsClientId=client)
        if person is not None and f.get("target"):
            p.resetBasePositionAndOrientation(person, f["target"], [0, 0, 0, 1], physicsClientId=client)
        eye = [pos[0] - 2.5, pos[1] - 2.5, pos[2] + 1.6]
        view = p.computeViewMatrix(eye, pos, [0, 0, 1], physicsClientId=client)
        _, _, rgb, _, _ = p.getCameraImage(args.w, args.h, viewMatrix=view, projectionMatrix=proj, renderer=p.ER_TINY_RENDERER, physicsClientId=client)
        img = np.reshape(np.asarray(rgb, dtype=np.uint8), (args.h, args.w, 4))[:, :, :3].copy()
        if cam_down is not None:
            sub, _ = cam_down.render(np.array(pos), client)
            b = f.get("bbox")
            if b and b[0] > 0.5:
                x0, y0, x1, y1 = [int(v) for v in cam_down.bbox_to_pixels({"vis": b[0], "cx": b[1], "cy": b[2], "w": b[3], "h": b[4]})]
                x0, x1 = max(0, x0), min(319, x1)
                y0, y1 = max(0, y0), min(239, y1)
                sub[y0:y1 + 1, [x0, x1]] = [255, 60, 60]
                sub[[y0, y1], x0:x1 + 1] = [255, 60, 60]
            img[8:248, args.w - 328:args.w - 8] = sub
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    p.disconnect(client)
    print(f"ghi {out} ({len(frames)} khung @ {args.fps} fps từ {traj_path})")


if __name__ == "__main__":
    main()

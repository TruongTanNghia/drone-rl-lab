"""Đo FPS YOLO ONNX trên CPU laptop: khởi động 100 khung, đo 300 khung (G4 cổng b).

    python scripts/bench_yolo.py --model perception/weights/yolo_target.onnx --images perception/data/sim_person/images/test
Ghi docs/yolo_bench.json.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.util import ROOT, now_iso  # noqa: E402
from perception.yolo_onnx import YoloOnnx  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="perception/weights/yolo_target.onnx")
    ap.add_argument("--images", default="perception/data/sim_person/images/test")
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--out", default="docs/yolo_bench.json")
    args = ap.parse_args()
    if not Path(args.model).exists():
        print(f"chưa có model {args.model} (chưa train YOLO)", file=sys.stderr)
        sys.exit(1)
    from PIL import Image

    paths = sorted(Path(args.images).glob("*.jpg"))
    if not paths:
        print("không có ảnh", file=sys.stderr)
        sys.exit(1)
    imgs = [np.asarray(Image.open(p).convert("RGB")) for p in paths[:64]]
    yolo = YoloOnnx(args.model, threads=args.threads)
    for i in range(args.warmup):
        yolo.detect(imgs[i % len(imgs)])
    t0 = time.perf_counter()
    n_det = 0
    for i in range(args.frames):
        n_det += len(yolo.detect(imgs[i % len(imgs)]))
    dt = time.perf_counter() - t0
    res = {
        "measured_at": now_iso(),
        "model": args.model,
        "imgsz": yolo.imgsz,
        "providers": yolo.providers,
        "cpu": platform.processor(),
        "warmup_frames": args.warmup,
        "frames": args.frames,
        "seconds": round(dt, 3),
        "fps": round(args.frames / dt, 2),
        "ms_per_frame": round(dt / args.frames * 1000, 2),
        "detections_total": n_det,
        "n_images_cycled": len(imgs),
    }
    (ROOT / args.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

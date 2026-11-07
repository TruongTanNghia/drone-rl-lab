# Drone RL Lab — huấn luyện drone bằng RL + DL theo giai đoạn

Hệ thống huấn luyện drone CF2X trong mô phỏng PyBullet (gym-pybullet-drones): **RL** (PPO, Stable-Baselines3) lo điều khiển, **DL** (YOLO nano → ONNX) lo nhận thức. Làm lần lượt G0 → G5 trên một bộ khung cố định (5 giao diện chốt ở G0). Mọi con số trong tài liệu/giao diện đều đọc từ `results/<run_id>/eval/*/metrics.json`; không có dữ liệu mẫu.

**Trạng thái:** G0 ĐẠT (xem `docs/report_G0.md`). G1–G5: mã nguồn đã có, **chưa train** — bảng kết quả sẽ sinh tự động khi có metrics.

## Cài đặt (Windows 11, không GPU, Python 3.12)
```
uv venv .venv --python 3.12.12
uv pip install --python .venv/Scripts/python.exe -r requirements.lock.txt        # pybullet build từ sdist, cần MSVC
uv pip install --python .venv/Scripts/python.exe -e third_party/gym-pybullet-drones --no-deps
cd app/web && npm install
```
`third_party/gym-pybullet-drones` là clone nhánh `main` (commit `348b5c1`). Ghi chú đọc mã nguồn: `docs/library_notes.md`. Máy và tốc độ mô phỏng: `docs/machine.md`.

## Chạy
```
python train.py --config configs/g1_hover.yaml --seed 0            # luôn gui=False
python evaluate.py --run results/<run_id> --controller ppo --episodes 100
python evaluate.py --run results/<run_id> --controller pid --episodes 100
python evaluate.py --run results/<run_id> --controller ppo --source yolo --episodes 100   # G4
python scripts/eval_checkpoints.py --run results/<run_id> --episodes 3   # bay thử mỗi checkpoint → timeline/ (dashboard "Xem lại quá trình huấn luyện")
python scripts/make_report.py                                        # docs/report_final.md
python scripts/make_report.py --phase g1 --inject docs/report_G1.md
python -m pytest
```
Viewer độc lập: mở `viewer/index.html` (kéo thả `traj_<seed>.json`) hoặc `python scripts/screenshot_viewer.py <traj> <png>`.

Dashboard G5 (FastAPI + Next.js + Three.js):
```
.venv/Scripts/uvicorn app.api.main:app --port 8000
cd app/web && npm run dev            # http://localhost:3000, /api/* được proxy sang FastAPI
```

## Cấu trúc
```
train.py  evaluate.py  configs/  core/ (config pydantic, util)  envs/ (BaseTask, SmokeEnv, HoverTask, WaypointTask, ObstacleTask, TargetTask)
perception/ (encoders, camera, bbox_sources, yolo_onnx, make_dataset, train_yolo_colab.ipynb)
agents/ (controllers: Random/PID/APF/BBoxServo/SB3; model_factory)   evaluation/ (runner, metrics, trajectory)
viewer/ (index.html Three.js + models/cf2.glb)   app/api (FastAPI)   app/web (Next.js 16)   scripts/   tests/   docs/   results/
```

## Luật của dự án (từ prompt)
Không làm giả kết quả · không hạ chuẩn cổng · báo "xong" kèm bằng chứng · CPU-first · train không render · đọc mã nguồn thư viện trước khi dùng · mọi thay đổi ghi `docs/experiments.md` · dừng ở mỗi cổng · seed train 0–8999, seed đánh giá ≥ 9000.

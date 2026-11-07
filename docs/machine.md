# Máy chạy và tốc độ mô phỏng

Đo bằng `python scripts/bench_env.py --config configs/g0_smoke.yaml --steps 3000` lúc 2026-11-07 20:23 (+07), dữ liệu gốc ở `docs/machine_bench.json`.

| Mục | Giá trị |
|---|---|
| CPU | AMD Ryzen 5 4600H, 6 nhân / 12 luồng |
| RAM | 31.4 GB |
| GPU | RTX 3050 Laptop (không dùng; mọi thứ chạy CPU, torch 2.15.0+cpu) |
| OS | Windows 11 10.0.26300 |
| Python | 3.12.12 (uv venv `.venv`), không có Conda → dùng venv |
| PyBullet | 3.2.7 build từ sdist bằng MSVC 14.51 (D:\Visual Studio\Packages) |
| `n_envs` auto | 5 (= 6 nhân − 1) |

## Số bước mô phỏng mỗi giây (ctrl 30 Hz, pyb 240 Hz, VEL + DSLPID, không render)

| Chế độ | 1 env | 5 env (SubprocVecEnv, spawn) |
|---|---|---|
| giữ yên (không reset) | **1 210.8** | **3 266.1** |
| hành động ngẫu nhiên (reset liên tục, 58 reset / 3000 bước) | 687.2 | 946.0 |

- Mỗi `reset()` tốn **36.7 ms** (`p.resetSimulation` + nạp lại URDF). Với lượt dài 300 bước (G1) reset chiếm ~13 % thời gian; lượt ngắn do rơi sớm thì reset chiếm phần lớn.
- Train G0 thực tế (`results/g0_ppo_s0_20261107-2024/train_meta.json`): 20 480 bước PPO trong 19.0 s = **1 076 bước/s** tính cả cập nhật mạng (lượt ngắn ~175 bước do agent chưa học, chạy song song với script hiệu chỉnh nên có bị tranh CPU).

## Ước lượng thời gian train (ở 5 env)
Giả sử ~2 000–2 500 bước/s khi lượt dài (gồm cả cập nhật PPO):

| Giai đoạn | total_steps | Thời gian ước tính / seed | 3 seed |
|---|---|---|---|
| G1 hover | 1.5 M | 10–13 phút | ~40 phút |
| G2 waypoint | 3 M | 20–25 phút | ~1.2 h |
| G3 obstacle (thêm 16 tia/bước) | 4 M | 30–45 phút | ~2 h |
| G4 target (nguồn sim) | 3 M | 20–30 phút | ~1.5 h |

Tất cả nằm trong giới hạn "một đêm" của prompt. Nếu kết quả cần thêm bước, còn dư ngân sách thời gian rất nhiều.

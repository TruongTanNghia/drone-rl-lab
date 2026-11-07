# Báo cáo tổng hợp (sinh tự động bởi scripts/make_report.py)

Mọi số liệu đọc từ `results/*/eval/*/metrics.json`. Chưa chạy thì ghi "chưa chạy".


## G0

- PPO: quy tắc `n_episodes >= 5.0`, giá trị từng seed = 5, trung bình = 5 → **ĐẠT**; seed kém nhất: `g0_ppo_s0_20261107-2024` (5, rơi 0 lượt)
  - điều kiện phụ (kiểm tay): pytest xanh
  - điều kiện phụ (kiểm tay): train 20000 bước không lỗi
  - điều kiện phụ (kiểm tay): viewer mở được quỹ đạo

| Controller | run / seed train | lượt | sai số TB sau 3 s (m) | cắt lượt | rơi | tỷ lệ đạt | return TB | Cổng |
|---|---|---|---|---|---|---|---|---|
| PPO | `g0_ppo_s0_20261107-2024` | 5 | 0.510 | 0 | 0 | 0 | 461.083 | ĐẠT |
| PIDBaseline | `g0_ppo_s0_20261107-2024` | 5 | 0.019 | 0 | 0 | 1 | 479.396 | ĐẠT |
| Random | `g0_ppo_s0_20261107-2024` | 5 | — | 5 | 5 | 0 | 58.360 | ĐẠT |

Nguồn: `results/g0_ppo_s0_20261107-2024/eval/pid/metrics.json`, `results/g0_ppo_s0_20261107-2024/eval/ppo/metrics.json`, `results/g0_ppo_s0_20261107-2024/eval/random/metrics.json`


## G1

**Cổng:** CHƯA CHẠY

_Chưa có metrics.json nào cho G1 (chưa chạy)._


## G2

**Cổng:** CHƯA CHẠY

_Chưa có metrics.json nào cho G2 (chưa chạy)._


## G3

**Cổng:** CHƯA CHẠY

_Chưa có metrics.json nào cho G3 (chưa chạy)._


## G4

**Cổng:** CHƯA CHẠY

_Chưa có metrics.json nào cho G4 (chưa chạy)._

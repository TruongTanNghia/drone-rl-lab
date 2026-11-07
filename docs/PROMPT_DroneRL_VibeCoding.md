# PROMPT — Drone RL Lab: huấn luyện drone bằng RL + DL theo giai đoạn

> **Cách dùng:** mở một thư mục rỗng trong Claude Code (hoặc Cursor), chép file `ui_reference.html` vào đó, rồi dán toàn bộ prompt này. Agent làm lần lượt G0 → G5. Hết mỗi giai đoạn agent phải dừng ở cổng nghiệm thu, nộp báo cáo, và chờ bạn gõ `tiếp G<n+1>`.

---

## 0. Vai trò và luật bắt buộc

Bạn là kỹ sư robotics/ML, xây một hệ thống huấn luyện drone trong mô phỏng: **RL** lo điều khiển, **DL** lo nhận thức (YOLO). Làm từng giai đoạn trên một bộ khung cố định.

Các luật sau không được vi phạm, kể cả khi làm vậy sẽ qua cổng nhanh hơn:

1. **Không làm giả kết quả.** Mọi con số trong báo cáo, README hay giao diện đều phải đọc từ file kết quả của một lần chạy thật trong `results/`. Không hardcode, không mock, không "số minh họa" trông giống kết quả. Chưa chạy thì ghi "chưa chạy".
2. **Không hạ chuẩn để qua cổng.** Không sửa ngưỡng cổng, không giảm số lượt đánh giá, không đánh giá trên seed đã dùng để train, không chọn riêng seed đẹp.
3. **Báo "xong" phải kèm bằng chứng.** Dán lệnh đã chạy và phần cuối output thật. Test phải chạy thật bằng `pytest`.
4. **Ưu tiên CPU.** Trừ bước train YOLO, mọi thứ phải chạy được trên laptop không có GPU rời. Không dùng Isaac Sim, Isaac Gym, Aerial Gym, AirSim hay Unreal.
5. **Train không render.** Khi train luôn để `gui=False`. 3D chỉ dùng để xem lại từ file quỹ đạo.
6. **Đọc mã nguồn thư viện trước khi dùng.** Không đoán tên hàm hay tham số. Ghi rõ phiên bản thư viện đang dùng.
7. **Mọi thay đổi phải có dấu vết.** Đổi reward, hyperparameter hay curriculum thì sửa trong file YAML và ghi một dòng vào `docs/experiments.md`: ngày, đổi gì, vì sao, kết quả.
8. **Dừng ở mỗi cổng.** Hết giai đoạn thì viết báo cáo theo mẫu ở mục 9 rồi dừng lại.
9. **Thiếu thông tin thì dùng mặc định ở mục 1 và ghi rõ giả định.** Chỉ hỏi khi gặp quyết định không đảo ngược được.

---

## 1. Bối cảnh và giá trị mặc định

| Mục | Mặc định (dùng khi người dùng chưa trả lời) |
|---|---|
| Nhiệm vụ cuối | Drone bay tới khu vực chỉ định, né vật cản, phát hiện người qua camera nhìn xuống rồi bám theo |
| Phạm vi | Chỉ làm trong mô phỏng. Drone thật là G6 tùy chọn, chỉ làm khi người dùng xác nhận có phần cứng |
| Máy chạy | Laptop không GPU rời, Windows 11, 4 nhân, 16 GB RAM |
| Python | 3.10 qua Conda. PyBullet không có wheel dựng sẵn cho Python mới hơn trên nhiều nền tảng. Nếu `pip` báo lỗi biên dịch trên Windows thì dùng `conda install -c conda-forge pybullet` hoặc chạy trong WSL2 Ubuntu |
| GPU | Chỉ dùng Google Colab hoặc Kaggle (miễn phí), và chỉ để train YOLO |
| Thời gian train | Mỗi giai đoạn tối đa khoảng một đêm (8 giờ) trên laptop |

**Tin nhắn đầu tiên của bạn** gồm ba phần:
1. Hỏi người dùng 4 câu: hệ điều hành, số nhân CPU và RAM; hạn nộp; nhiệm vụ cuối của drone; có bay drone thật không. Người dùng trả lời "dùng mặc định" thì theo bảng trên.
2. Tóm tắt kế hoạch G0 trong 5–7 dòng.
3. Bắt tay làm G0.

---

## 2. Công nghệ

| Vai trò | Dùng | Ghi chú |
|---|---|---|
| Mô phỏng | [gym-pybullet-drones](https://github.com/utiasDSL/gym-pybullet-drones) (nhánh `main`) | `git clone` rồi `pip install -e .`. Drone `DroneModel.CF2X` |
| API môi trường | Gymnasium | Kế thừa `BaseRLAviary`, giống cách `HoverAviary` đang làm |
| RL | [Stable-Baselines3](https://stable-baselines3.readthedocs.io) PPO, có thể thêm SAC để so sánh | `SubprocVecEnv` + `VecNormalize` |
| DL | [Ultralytics](https://docs.ultralytics.com) YOLO bản nano mới nhất, xuất ONNX | Laptop chạy bằng `onnxruntime`, `CPUExecutionProvider` |
| Cấu hình | PyYAML + pydantic | Mỗi thí nghiệm là một file YAML |
| Log | CSV + TensorBoard | |
| Test | pytest | |
| Viewer | Three.js, một file HTML | Phải chạy được trên card onboard |
| Dashboard (G5) | FastAPI + React (Vite, TypeScript) | **Không dùng Streamlit** |

Cài xong thì chạy `pip freeze > requirements.lock.txt` và commit file đó.

---

## 3. Cấu trúc repo

```text
drone-rl/
├── README.md
├── train.py              # python train.py --config configs/g1_hover.yaml --seed 0
├── evaluate.py           # python evaluate.py --run results/<run_id> --controller ppo --episodes 100
├── configs/              # g0_smoke.yaml, g1_hover.yaml, g2_waypoint.yaml, g3_obstacle.yaml, g4_target.yaml
├── envs/                 # các env kế thừa BaseRLAviary: HoverTask, WaypointTask, ObstacleTask, TargetTask
├── perception/           # encoder trạng thái, camera, sinh dữ liệu ảnh, YOLO ONNX
├── agents/               # tạo model SB3, các baseline PID / APF / bám khung
├── evaluation/           # chạy N lượt, tính chỉ số, ghi quỹ đạo (thư mục "eval/" trong kế hoạch)
├── viewer/               # index.html Three.js phát lại quỹ đạo
├── app/                  # G5: api/ (FastAPI) và web/ (React)
├── scripts/              # make_report.py, record_video.py, bench_yolo.py
├── results/              # mỗi lần chạy một thư mục; không commit model và file nặng
├── docs/                 # machine.md, library_notes.md, experiments.md, report_G0.md ... report_G5.md
└── tests/
```

---

## 4. Năm giao diện chốt ở G0

Năm giao diện này **không được đổi** sau G0. Giai đoạn sau chỉ thêm class mới theo đúng các giao diện này.

### 4.1 Môi trường
- Kế thừa `BaseRLAviary` và theo API Gymnasium: `reset(seed=...) -> (obs, info)`, `step(action) -> (obs, reward, terminated, truncated, info)`.
- Ghi đè cả `_observationSpace` lẫn `_computeObs`. Quan sát mặc định của `BaseRLAviary` với `ObservationType.KIN` có kèm bộ đệm hành động dài nửa giây, ta không dùng nó.
- `info` có tối thiểu các trường: `t`, `pos`, `vel`, `rpy`, `goal`, `events` (list), `success`, `crashed`, `reason`.
- Hành động dùng `ActionType.VEL`: 4 giá trị, gồm 3 giá trị hướng và 1 hệ số tốc độ, đi qua `DSLPIDControl` có sẵn. **Lưu ý:** `SPEED_LIMIT` mặc định bằng 0,03 × `MAX_SPEED_KMH` (đổi sang m/s), rất chậm với CF2X. Phải in ra giá trị thực ở G0 rồi ghi đè bằng `env.speed_limit` trong config.

### 4.2 Bộ mã hóa nhận thức
```python
class Encoder(Protocol):
    dim: int
    def encode(self, raw: dict) -> np.ndarray: ...
```
- G0–G3 dùng `StateEncoder`.
- G4 dùng `TargetEncoder(source="sim" | "yolo")`. Hai nguồn **phải cùng `dim` và cùng thứ tự trường**, nhờ vậy policy train bằng nguồn `sim` chạy được ngay với nguồn `yolo`.

### 4.3 Bộ điều khiển
```python
class Controller(Protocol):
    name: str
    def reset(self, seed: int) -> None: ...
    def act(self, obs: np.ndarray, info: dict) -> np.ndarray: ...
```
Policy SB3 được bọc trong `SB3Controller`, nạp kèm `vecnormalize.pkl`. Các baseline gồm `RandomController`, `PIDBaseline`, `APFBaseline` và `BBoxServoBaseline`, cùng ra lệnh `ActionType.VEL` như policy. Phần đánh giá chỉ gọi đúng giao diện này.

### 4.4 Cấu hình
Mỗi thí nghiệm là một file YAML, được kiểm bằng pydantic. File sai khóa thì báo lỗi ngay, không lặng lẽ bỏ qua. Xem ví dụ ở mục 5.1.

### 4.5 Kết quả
```text
results/<run_id>/                 # run_id = <phase>_<algo>_s<seed>_<YYYYmmdd-HHMM>
├── config.yaml                   # bản sao config đã dùng
├── model.zip, vecnormalize.pkl
├── train_log.csv                 # timesteps, ep_rew_mean, ep_len_mean, success_rate, wall_time
├── tb/                           # TensorBoard
└── eval/<controller>[_<source>]/
    ├── metrics.json
    └── traj_<seed>.json
```
Seed của các lượt train lấy trong khoảng 0–8999. Seed đánh giá bắt đầu từ 9000. `evaluate.py` phải **từ chối chạy** nếu hai khoảng này chồng lên nhau.

---

## 5. Định dạng file

### 5.1 Config (ví dụ G2)
```yaml
phase: g2
env:
  ctrl_freq: 30
  pyb_freq: 240
  episode_sec: 40
  speed_limit: 1.5            # m/s, ghi đè SPEED_LIMIT mặc định
  waypoints: {count: 4, box: [[-4, 4], [-4, 4], [1, 3]], min_gap: 2.5, reach_radius: 0.35}
  randomization: {wind_max: 2.0, gust_sigma: 0.8, gust_tau: 2.0, mass_scale: [0.8, 1.2]}
  curriculum:
    - {name: one_wp_calm, overrides: {waypoint_count: 1, wind_max: 0.0}, promote_at: 0.8}
    - {name: full, overrides: {}, promote_at: null}
reward: {progress: 5.0, reach_bonus: 10.0, time_penalty: 0.03, crash: -50.0}
algo:
  name: ppo
  total_steps: 3000000        # chỉnh lại theo tốc độ steps/giây đo ở G0
  n_envs: auto                # số nhân CPU trừ 1
  policy_kwargs: {net_arch: {pi: [64, 64], vf: [64, 64]}, log_std_init: -1.0}
  vecnormalize: {obs: true, reward: true}
train_seeds: [0, 1, 2]
eval: {episodes: 100, seed0: 9000}
gate: {metric: success_rate, op: ">=", value: 0.90}
```

### 5.2 `metrics.json`
```json
{
  "schema": "drone-metrics/1",
  "run_id": "g2_ppo_s0_20261107-0130",
  "phase": "g2",
  "controller": "ppo",
  "source": "sim",
  "train_seed": 0,
  "config_hash": "sha256:...",
  "git_commit": "...",
  "created_at": "ISO-8601",
  "eval_seeds": [9000, 9099],
  "n_episodes": 100,
  "metrics": { "success_rate": "<số thật>", "crash_count": "<số thật>", "...": "..." },
  "gate": { "name": "G2", "rule": "success_rate >= 0.90", "passed": "<true|false>" }
}
```

### 5.3 Quỹ đạo `traj_<seed>.json`
Hệ tọa độ thế giới tính bằng mét: x hướng trước, y hướng trái, z hướng lên. Viewer đổi sang Three.js theo phép `(x, z, -y)`.
```json
{
  "schema": "drone-traj/1",
  "phase": "g3", "run_id": "...", "controller": "ppo", "seed": 9000,
  "dt": 0.0333, "mass_scale": 1.08,
  "world": {
    "goal": [6, 0.4, 1.2],
    "waypoints": [],
    "obstacles": [{"x": 0.5, "y": -1.2, "r": 0.4, "h": 4}],
    "arena": {"x": [-7, 7], "y": [-6, 6], "z_max": 4}
  },
  "frames": [
    {"t": 0.0, "p": [-6, 0.1, 1.2], "v": [0, 0, 0], "rpy": [0, 0, 0], "wp": 0,
     "wind": [0.3, -0.1], "rays": [4.0, 3.2], "target": null, "bbox": null}
  ],
  "events": [{"t": 3.2, "kind": "good", "text": "Chạm điểm 1/4"}],
  "outcome": {"success": true, "crashed": false, "reason": ""}
}
```
Trường nào giai đoạn đó không có thì để `null` hoặc list rỗng. Không bỏ hẳn khóa.

---

## 6. Các giai đoạn

### G0 — Bộ khung chuẩn
**Mục tiêu:** khung chạy trọn vòng "train → đánh giá → xem lại" với một agent ngẫu nhiên, chưa cần học được gì.

Việc cần làm:
1. Tạo môi trường Conda, cài gym-pybullet-drones, chạy một ví dụ có sẵn ở chế độ không GUI để chắc chắn đã cài đúng.
2. Đọc `BaseAviary.py`, `BaseRLAviary.py`, `HoverAviary.py`, `DSLPIDControl.py` rồi ghi `docs/library_notes.md`. Nội dung gồm: tần số mô phỏng và điều khiển, không gian quan sát và hành động, giá trị `SPEED_LIMIT` thực của `VEL`, `IMG_RES`, cách lấy ảnh camera, cách áp lực ngoài (`p.applyExternalForce`), cách đổi khối lượng (`p.changeDynamics`), cách bắn tia (`p.rayTestBatch`).
3. Dựng repo theo mục 3, cài đặt 5 giao diện ở mục 4 và config pydantic.
4. Viết `SmokeEnv` (bọc `HoverAviary` theo giao diện mục 4.1), `RandomController`, `evaluate.py` và phần ghi quỹ đạo.
5. Viết `viewer/index.html`: mở file quỹ đạo bằng ô chọn file hoặc kéo thả; có phát, tạm dừng, tua, tốc độ 1×/2×/4×; vẽ drone, vệt bay, đích, waypoint, cột và mục tiêu nếu có. Để chạy được trên card onboard: `pixelRatio ≤ 1,5`, không đổ bóng, vật liệu Lambert. Tham khảo bố cục và màu ở `ui_reference.html`.
6. Viết test (mục 8), đo **số bước mô phỏng mỗi giây** ở chế độ không render với 1 env và với `n_envs` env, rồi ghi vào `docs/machine.md`.

**Cổng 0 (kiểm tự động):**
- `pytest` xanh hết.
- `python train.py --config configs/g0_smoke.yaml` chạy PPO 20.000 bước không lỗi và tạo đủ file như mục 4.5.
- `python evaluate.py ... --controller random --episodes 5` tạo được `metrics.json` và quỹ đạo.
- Viewer mở được file quỹ đạo vừa tạo. Nếu có Playwright thì chụp màn hình làm bằng chứng.
- Có số bước mỗi giây đo thật, kèm ước lượng thời gian train cho G1.

### G1 — Giữ độ cao
- **Env `HoverTask`:** `ctrl_freq` 30, episode 10 s, đích (0, 0, 1).
- **Điểm xuất phát ngẫu nhiên trên không:** x, y ∈ [−0,8; 0,8], z ∈ [0,3; 1,7]. **Không xuất phát dưới đất**, lý do ở mục 7.
- **Quan sát (12):** (đích − vị trí), vận tốc, roll/pitch/yaw, vận tốc góc; mỗi nhóm chia cho thang đo ghi trong config.
- **Reward khởi điểm:** `exp(-2·d) - 0.05·‖v‖`. Bị cắt lượt (|x| hoặc |y| > 2, z > 2,5, |roll| hoặc |pitch| > 0,8 rad) thì −10.
- **Train:** PPO, `n_envs` bằng số nhân trừ 1, `VecNormalize`, `log_std_init = -1`, mạng 64×64. Tổng số bước tính từ số đo ở G0. Train 3 seed: 0, 1, 2.
- **`PIDBaseline`:** lệnh `VEL` hướng về đích, hệ số tốc độ `clip(k·d / speed_limit, 0, 1)`.
- **Chỉ số:** sai số vị trí trung bình sau giây thứ 3 (m), số lần bị cắt lượt, tỷ lệ đạt (không rơi và sai số dưới 0,1 m).

**Cổng 1:** đánh giá 100 lượt (seed 9000–9099). Sai số trung bình qua 3 seed dưới 0,1 m, và **không seed nào bị rơi lần nào**. Báo cáo dạng trung bình ± độ lệch chuẩn qua 3 seed, đặt cạnh PID.

### G2 — Bay theo điểm, có gió
- **Env `WaypointTask`:** 4 waypoint ngẫu nhiên trong hộp x, y ∈ [−4; 4], z ∈ [1; 3]; hai điểm liên tiếp cách nhau ít nhất 2,5 m; chạm khi cách dưới 0,35 m. Episode 40 s, `speed_limit` 1,5 m/s.
- **Gió:** gió nền nằm ngang, độ lớn ngẫu nhiên U(0; 2) m/s, hướng ngẫu nhiên; cộng gió giật theo quá trình Ornstein–Uhlenbeck (σ = 0,8, τ = 2 s). Áp vào drone mỗi bước PyBullet bằng `p.applyExternalForce(..., p.WORLD_FRAME)` với lực `c_d·(gió − v_xy)`. Tự hiệu chỉnh `c_d` sao cho gió 2 m/s gây trôi thấy rõ, và ghi lại trong `library_notes.md`.
- **Khối lượng:** nhân ngẫu nhiên ×0,8–1,2 bằng `p.changeDynamics`. Bộ PID bên trong vẫn dùng khối lượng danh định; mục đích chính là để chênh lệch này kiểm độ bền.
- **Quan sát:** như G1 nhưng đích là waypoint hiện tại, thêm 1 trường tiến độ (số điểm đã chạm / 4). Không đưa gió vào quan sát.
- **Reward:** `5·(d_trước − d) + 10` mỗi lần chạm điểm, `− 0.03` mỗi bước, rơi thì −50. **Bắt buộc có phạt theo thời gian**, lý do ở mục 7.
- **Curriculum:** bắt đầu với 1 điểm, không gió. Lên mức "đầy đủ" khi tỷ lệ thành công trên 100 lượt gần nhất từ 80%. Viết thành callback, ghi thời điểm chuyển mức vào log.
- **Chỉ số:** tỷ lệ chạm đủ 4 điểm, thời gian hoàn thành trung bình, số điểm chạm trung bình, số lần rơi. So với `PIDBaseline`.

**Cổng 2:** trên 100 lượt chưa thấy, bật đủ gió và đổi khối lượng: tỷ lệ thành công trung bình 3 seed từ 90%. Ghi thêm kết quả của seed kém nhất.

### G3 — Né vật cản
- **Env `ObstacleTask`:** vùng bay x ∈ [−7; 7], y ∈ [−6; 6]. Xuất phát ở x = −6, đích ở x = +6, y ngẫu nhiên trong [−2; 2], z = 1,2.
- **Vật cản:** 9 cột hình trụ, bán kính U(0,3; 0,6), cao 4 m, đặt trong x ∈ [−3,5; 3,5], y ∈ [−4; 4]. Tâm hai cột cách nhau ít nhất r₁ + r₂ + 1,1 m. Sau khi đặt, kiểm bằng BFS trên lưới (bán kính drone 0,25 m) rằng có đường đi; không có thì sinh lại bản đồ.
- **Cảm biến:** 16 tia ngang dài 4 m, bắn bằng `p.rayTestBatch`. Điểm đầu tia đặt cách tâm drone 0,12 m để tia không trúng chính thân drone.
- **Quan sát:** (đích − vị trí)/6, vận tốc, rpy, vận tốc góc, 16 giá trị `1 − d/4`. Bản thí nghiệm phụ thêm 2 trường vector đẩy tính từ các tia.
- **Reward:** `5·Δd − 0.03` mỗi bước, `− 0.1·max(0, 0.6 − d_min)`. Tới đích (cách dưới 0,5 m theo phương ngang và 0,6 m theo phương đứng) thì +50. Va chạm thì −50; phát hiện va chạm bằng `p.getContactPoints` giữa drone và cột. Episode 30 s, gió nhẹ 0,5 m/s.
- **`APFBaseline` dùng đúng các tia:** thành phần hút về đích, tối đa 1,5 m/s; tia nào có khoảng hở dưới 1,0 m thì sinh thành phần đẩy, độ lớn `0.4·(1/d − 1)`; thêm thành phần tiếp tuyến hệ số 0,6, giữ cố định chiều vòng cho tới khi thoát vật cản (hysteresis). Chỉnh lại thông số trong PyBullet và ghi vào `experiments.md`.
- **Chỉ số:** tỷ lệ tới đích không va chạm, số va chạm, thời gian, khoảng hở nhỏ nhất.
- **Bảng thí nghiệm phụ (ablation):** chỉ tia so với tia + vector đẩy. Có thể thêm PPO so với SAC.

**Cổng 3:** trên 100 bản đồ chưa thấy (seed 9000–9099), tỷ lệ thành công trung bình 3 seed từ 85%.

### G4 — Tìm và bám mục tiêu (RL + DL)
**Phần A — mục tiêu và camera**
- Mục tiêu là một "người" dựng từ hình khối, cao khoảng 1,7 m. Đi ngẫu nhiên với tốc độ 1,0–1,4 m/s, tự quay đầu khi ra quá bán kính 9 m. Mỗi bước cập nhật vị trí bằng `p.resetBasePositionAndOrientation`.
- Camera có gimbal, nhìn thẳng xuống. FOV ngang 70°, ảnh 320×240, render bằng `p.ER_TINY_RENDERER` (chạy trên CPU). Drone giữ độ cao 4 m.
- **Nguồn `sim` (dùng khi train):** chiếu tâm và kích thước mục tiêu lên ảnh theo mô hình pinhole, ra `vis, cx, cy, w, h` với cx, cy ∈ [−1; 1]. Cộng nhiễu σ = 0,03; bỏ mất 8% số khung; mục tiêu sát mép ảnh thì coi như không thấy. **Bắt buộc có nhiễu**, nếu không policy sẽ hỏng khi gắn YOLO.

**Phần B — dữ liệu và YOLO**
- `perception/make_dataset.py`: render mặc định 4.000 ảnh với độ cao 2–8 m, vị trí mục tiêu ngẫu nhiên, đổi màu và vân mặt đất, thêm vật gây nhiễu. Nhãn lấy tự động từ ảnh segmentation của `getCameraImage` (theo id của mục tiêu) rồi ghi theo định dạng YOLO. Chia train/val/test **theo seed cảnh** để không rò rỉ dữ liệu.
- Có thể trộn thêm VisDrone (Ultralytics có sẵn `VisDrone.yaml`) với lớp người đi bộ. Nếu trộn thì báo mAP trên VisDrone riêng.
- `perception/train_yolo_colab.ipynb`: train YOLO nano với `imgsz=320` trên GPU Colab, xuất ONNX, ghi mAP50 trên tập test mô phỏng.
- `perception/yolo_onnx.py` chạy bằng onnxruntime trên CPU. `scripts/bench_yolo.py` đo FPS trên laptop thật: khởi động 100 khung, đo 300 khung.

**Phần C — RL**
- **Env `TargetTask`:** train với `TargetEncoder(source="sim")`.
- **Quan sát (14):** `vis, cx, cy, w, h`, `z − 4`, vận tốc, rpy, vận tốc góc.
- **Reward:** nếu mục tiêu thật sự nằm trong khung thì `1 − 0.5·(cx² + cy²)`, nếu không thì −0,5. Trừ thêm `0.1·|z − 4|`. Rơi thì −50. Episode 30 s.
- **`BBoxServoBaseline`:** từ tâm khung và độ cao, ước lượng độ lệch theo mét rồi ra lệnh vận tốc về phía mục tiêu. Mất mục tiêu thì bay lên thêm 1,5 m và giữ vị trí.
- **Đánh giá hai chế độ:** `source=sim` (giống lúc train) và `source=yolo`, render camera mỗi 1–2 bước điều khiển rồi đưa khung của YOLO vào policy. Báo cáo rõ khoảng chênh giữa hai chế độ.

**Cổng 4** (cả ba điều kiện):
- (a) mAP50 của YOLO từ 0,7 trên tập test mô phỏng.
- (b) Từ 10 FPS ở ảnh 320 px trên CPU của laptop.
- (c) Ở chế độ `source=yolo`, policy giữ mục tiêu trong khung từ 80% thời gian, tính trung bình 100 lượt × 3 seed.

### G5 — Demo và báo cáo
- **`app/api` (FastAPI, chỉ đọc `results/`):** `GET /api/runs`, `/api/runs/{id}`, `/api/runs/{id}/eval/{controller}/metrics`, `/api/runs/{id}/eval/{controller}/traj/{seed}`, `/api/runs/{id}/curve` (đọc từ `train_log.csv`). Không có dữ liệu mẫu nào; thiếu file thì trả 404 kèm thông báo rõ ràng.
- **`app/web` (React + Vite + TypeScript):**
  - Trang lộ trình G0–G5, trạng thái cổng đọc từ `metrics.json`.
  - Trang chi tiết một run: biểu đồ học (Recharts), bảng policy so với baseline, viewer 3D (dùng lại `viewer/`), chọn seed để phát lại. Riêng G4 phát kèm ô camera và khung mục tiêu nếu file quỹ đạo có `bbox`.
  - Bố cục tham khảo `ui_reference.html`.
- **`scripts/make_report.py`:** sinh `docs/report_final.md` với mọi bảng số lấy từ các file metrics.
- **`scripts/record_video.py`:** ghép khung hình từ `getCameraImage` (chế độ DIRECT) bằng ffmpeg, mỗi giai đoạn một video.

**Cổng 5:**
- `uvicorn` và `npm run build` đều chạy được.
- Mọi con số trên giao diện truy được về file nguồn: rê chuột vào thì hiện `run_id` và đường dẫn file.
- Báo cáo được sinh tự động.
- Có đủ một video cho mỗi giai đoạn G1–G4.

### G6 — Drone thật (tùy chọn)
Chỉ làm khi người dùng xác nhận phần cứng (Crazyflie, Tello hoặc PX4). Đừng chuẩn bị trước.

---

## 7. Bài học từ bản demo trình duyệt (đã chạy thử)

Bản demo chạy vật lý rút gọn và học bằng CEM với policy tuyến tính, không phải PyBullet + PPO. Vì vậy các con số dưới đây **chỉ là bài học, không phải mục tiêu**.

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Drone học cách nằm im dưới đất, không cất cánh | Xuất phát dưới đất và reward giảm tuyến tính theo khoảng cách, nên nằm yên được điểm an toàn hơn mọi lần thử bay | Xuất phát trên không ở vị trí ngẫu nhiên; reward dương khi ở gần đích; phạt khi bay ra ngoài vùng |
| Policy bay theo điểm chậm gần gấp ba PID (29,6 s so với 10,1 s) | Có điểm thưởng nhỏ cho mỗi bước còn sống | Đổi sang phạt nhẹ theo thời gian. Sau khi đổi, bản demo còn 12,7 s |
| Chỉ dùng tia đo thì không né được cột (0%) | Policy tuyến tính khó tự suy ra hướng đẩy từ 12 tia | Thêm vector đẩy tính từ tia thì đạt 75–77%, vẫn chưa qua cổng 85%. Với PPO dùng MLP, hãy làm ablation có và không có vector đẩy |
| Policy ngẫu nhiên lúc đầu trôi ra khỏi vùng bay | Độ lệch ngẫu nhiên ở các kênh ngang quá lớn | Để `log_std_init` thấp và dùng `VecNormalize` |
| PID và APF đã chỉnh tốt đạt 100% ở G1–G3 trong demo | Bài toán mô phỏng còn dễ | Không sao. Mục đích là so sánh trung thực, không phải để RL thắng bằng mọi giá |

---

## 8. Kiểm tra chống làm giả (bắt buộc, chạy trong `pytest`)

1. `test_env_check`: mọi env qua `stable_baselines3.common.env_checker.check_env`.
2. `test_determinism`: cùng seed và cùng controller thì hai lần chạy cho quỹ đạo giống hệt nhau (so mã băm).
3. `test_random_vs_baseline`: chỉ số của `RandomController` phải khác hẳn chỉ số của baseline, để chắc bộ đo không trả hằng số.
4. `test_seed_split`: `evaluate.py` từ chối khi seed đánh giá chồng lên khoảng seed train.
5. `test_metrics_provenance`: mỗi `metrics.json` có đủ `run_id`, `config_hash`, `git_commit`, `eval_seeds`, `n_episodes`, `created_at`, và `config_hash` khớp với `config.yaml` trong thư mục run.
6. `test_report_numbers`: mọi con số trong các bảng của `docs/report_*.md` đều tìm thấy trong một file `metrics.json`.
7. `test_api_no_demo_data` (từ G5): khi `results/` trống, API trả danh sách rỗng hoặc 404, không trả dữ liệu mẫu.

---

## 9. Mẫu báo cáo cuối mỗi giai đoạn (`docs/report_G<n>.md`)

```markdown
## Báo cáo G<n>: <tên giai đoạn>
**Cổng:** ĐẠT / CHƯA ĐẠT (dòng này sinh từ metrics.json)

### Lệnh đã chạy
<chép nguyên văn các lệnh, kèm thời gian chạy thật>

### Kết quả (bảng sinh tự động)
| Controller | Chỉ số 1 | Chỉ số 2 | ... | Cổng |
| PPO (TB ± ĐLC, 3 seed) | ... |
| Baseline | ... |

### Đã thay đổi gì so với config gốc
<liên kết tới các dòng trong experiments.md>

### Quỹ đạo tiêu biểu
- Lượt thành công: results/.../traj_90xx.json
- Lượt thất bại: results/.../traj_90yy.json (giải thích vì sao thất bại)

### Vấn đề còn tồn và đề xuất cho giai đoạn sau
```

**Nếu chưa qua cổng:** được chỉnh tối đa 3 vòng (reward, hyperparameter, curriculum), mỗi vòng ghi vào `experiments.md`. Sau 3 vòng vẫn chưa qua thì nộp báo cáo chẩn đoán kèm đề xuất rồi dừng, chờ người dùng quyết định. Tuyệt đối không hạ ngưỡng.

---

## 10. Không được làm

- Dùng Streamlit cho dashboard.
- Bật GUI hay render lúc train.
- Đưa vị trí thật của mục tiêu vào quan sát của policy ở G4 (chỉ được dùng để tính reward và để chiếu ra khung ở nguồn `sim`).
- Đánh giá trên seed đã dùng để train, hoặc chọn riêng seed đẹp.
- Đổi 5 giao diện ở mục 4 sau khi đã qua G0.
- Commit model, dataset hay video vào git (dùng `.gitignore`).
- Viết README hay báo cáo khẳng định kết quả mà không có file metrics đi kèm.

# Ghi chú đọc mã nguồn gym-pybullet-drones

Phiên bản: `gym-pybullet-drones` 2.2.0, nhánh `main`, commit `348b5c18a4bb770a48928b9d044decf77ca33302` (2026-11-05), cài `pip install -e third_party/gym-pybullet-drones --no-deps`.
Thư viện kèm: pybullet 3.2.7 (build từ sdist bằng MSVC 14.51 vì PyPI không có wheel Windows), gymnasium 1.4.0, stable-baselines3 2.9.2, torch 2.15.0+cpu, numpy 2.5.4, Python 3.12.12.
Lưu ý: `pyproject.toml` của thư viện yêu cầu Python ^3.12, nên không dùng 3.10 như mặc định của prompt. Toàn bộ danh sách gói ở `requirements.lock.txt`.

Các giá trị dưới đây được in bằng `python scripts/library_values.py` (xem lệnh và output ở `report_G0.md`).

## Tần số
- `BaseAviary.__init__(pyb_freq=240, ctrl_freq=240)`; `HoverAviary` đặt `ctrl_freq=30`. Yêu cầu `pyb_freq % ctrl_freq == 0`. Với 240/30 → `PYB_STEPS_PER_CTRL = 8`, `CTRL_TIMESTEP = 1/30`, `PYB_TIMESTEP = 1/240`.
- `step()` gọi `_preprocessAction` một lần rồi lặp 8 lần `_physics` + `p.stepSimulation`; sau đó `_updateAndStoreKinematicInformation`, `_computeObs`, `_computeReward`, `_computeTerminated`, `_computeTruncated`, `_computeInfo`, rồi `step_counter += 8`.
- `reset()` gọi `p.resetSimulation` + `_housekeeping()` (nạp lại `plane.urdf` và drone từ `INIT_XYZS`) mỗi lượt → tốn ~37 ms/lượt (đo ở `machine_bench.json`).

## Không gian quan sát và hành động (BaseRLAviary)
- Trạng thái drone `_getDroneStateVector` dài 20: pos(3) quat(4) rpy(3) vel(3) ang_v(3) last_clipped_action(4).
- `ObservationType.KIN`: Box shape `(NUM_DRONES, 12 + ACTION_BUFFER_SIZE·4)`; 12 = pos, rpy, vel, ang_v; cộng bộ đệm hành động `ACTION_BUFFER_SIZE = ctrl_freq//2 = 15` khung (0,5 s). Với VEL: obs shape **(1, 72)**. Ta ghi đè cả `_observationSpace` và `_computeObs`, không dùng bộ đệm này.
- `ActionType.VEL`: Box `(1, 4)` trong [−1, 1]: 3 kênh hướng (chuẩn hóa về vector đơn vị) + kênh 4 là hệ số tốc độ `|target[3]|`. `_preprocessAction` gọi `DSLPIDControl.computeControl(target_pos = vị trí hiện tại, target_rpy = (0,0,yaw hiện tại), target_vel = SPEED_LIMIT·|a3|·u)`.
- `SPEED_LIMIT = 0.03 · MAX_SPEED_KMH · 1000/3600`. Với `cf2x.urdf` `max_speed_kmh=30` → **SPEED_LIMIT = 0.25 m/s** (đo thật). Quá chậm, nên `BaseTask` ghi đè `env.SPEED_LIMIT = cfg.env.speed_limit` ngay sau `super().__init__()`.
- Đáp ứng VEL thực tế (`scripts/calibrate.py`, lệnh bay ngang hết tốc 4 s, `docs/calibration.json`):

| speed_limit | v ổn định | v đỉnh | nghiêng tối đa (rad) |
|---|---|---|---|
| 0.25 | 0.26 | 0.33 | 0.14 |
| 0.5 | 0.51 | 0.68 | 0.31 |
| 1.0 | 0.98 | 1.40 | 0.55 |
| 1.5 | 1.47 | 2.08 | 0.70 |
| 2.0 | 1.96 | 2.73 | 0.86 |

  → G1 dùng 1.0 m/s với `max_tilt 0.8`; G2–G4 dùng 1.5 m/s với `max_tilt 1.2` (nghiêng đỉnh 0.70 + dự phòng gió/khối lượng).

## Tham số CF2X (`assets/cf2x.urdf`)
m = 0.027 kg, L = 0.0397 m, kf = 3.16e-10, km = 7.94e-12, thrust2weight = 2.25, HOVER_RPM ≈ 14468, MAX_RPM ≈ 21703, collision: trụ r = 0.06 m, h = 0.025 m. `Physics.PYB`: lực mỗi cánh `kf·rpm²` áp bằng `p.applyExternalForce(drone, link i, [0,0,f], [0,0,0], p.LINK_FRAME)`, mô-men yaw bằng `p.applyExternalTorque(..., link 4, p.LINK_FRAME)`.

## DSLPIDControl
- Hệ số vị trí P = [.4, .4, 1.25], I = [.05, .05, .05], D = [.2, .2, .5]; thái độ P = [70000, 70000, 60000], D = [20000, 20000, 12000]. Tích phân vị trí bị kẹp ±2 (z: ±0.15).
- `computeControl(control_timestep, cur_pos, cur_quat, cur_vel, cur_ang_vel, target_pos, target_rpy, target_vel, target_rpy_rates)` → `(rpm[4], pos_e, yaw_e)`. Bộ PID có bộ nhớ (`last_rpy`, tích phân) nên `BaseTask.reset()` gọi `ctrl.reset()` mỗi lượt (thư viện không làm việc này).
- `GRAVITY` của bộ điều khiển lấy từ URDF (khối lượng danh định), nên khi đổi khối lượng bằng `p.changeDynamics` PID vẫn tin m = 0.027 → tạo sai số để thử độ bền (đúng ý G2).

## Camera
- `vision_attributes=True` ⇒ `IMG_RES = [64, 48]` (ghi cứng trong `BaseAviary`), `IMG_FRAME_PER_SEC = 24`, `IMG_CAPTURE_FREQ = pyb_freq/24 = 10`. Với `ctrl_freq = 30` (8 bước/ctrl) thư viện **báo lỗi** "frequencies incompatible" (đã gặp khi chạy `library_values.py`), nên ta không dùng `ObservationType.RGB` mà tự render.
- `_getDroneImages`: `p.computeViewMatrix(eye = pos + [0,0,L], target = pos + R·[1000,0,0], up=[0,0,1])`, `p.computeProjectionMatrixFOV(fov=60, aspect=1, near=L, far=1000)`, `p.getCameraImage(w, h, shadow=1, viewMatrix, projectionMatrix, flags=ER_SEGMENTATION_MASK_OBJECT_AND_LINKINDEX)` trả `(w, h, rgb, dep, seg)`; `seg` là id vật thể (+ link) trên từng pixel → dùng để sinh nhãn YOLO ở G4. Ở chế độ DIRECT, mặc định renderer là `p.ER_TINY_RENDERER` (CPU). Camera G4 của ta ở `perception/camera.py`: FOV ngang 70° (PyBullet nhận FOV dọc, đổi `vfov = 2·atan(tan(35°)·H/W)` = 55.4° với 320×240), nhìn thẳng xuống, up = +x.

## Lực ngoài, khối lượng, tia
- Gió: `p.applyExternalForce(bodyId, linkIndex=-1, forceObj=[fx,fy,0], posObj=<vị trí thân trong hệ thế giới>, flags=p.WORLD_FRAME)` gọi **mỗi bước PyBullet** (lực ngoài bị xóa sau mỗi `stepSimulation`). `BaseTask._physics` gọi `super()._physics` rồi `_apply_wind`. Lực `c_d·(gió − v_xy)`. Hiệu chỉnh c_d với gió nền 2 m/s, drone giữ vị trí (lệnh 0) 6 s (`docs/calibration.json`):

| c_d (N·s/m) | lực lúc đứng yên | trôi sau 6 s |
|---|---|---|
| 0.005 | 10 mN | 0.36 m |
| 0.01 | 20 mN | 0.61 m |
| **0.02** | 40 mN (15 % trọng lượng 265 mN) | **1.09 m** |
| 0.03 | 60 mN | 1.44 m |
| 0.05 | 100 mN | 2.40 m |

  Chọn **c_d = 0.02**: gió 2 m/s gây trôi hơn 1 m, thấy rõ nhưng PID vẫn bù được.
- Gió giật: Ornstein–Uhlenbeck rời rạc `g += (−g/τ)·dt + σ·√(2/τ)·√dt·N(0,1)` (phương sai dừng = σ²), σ = 0.8, τ = 2 s, cập nhật mỗi bước PyBullet.
- Khối lượng: `p.changeDynamics(droneId, -1, mass=0.027·k)` sau `_housekeeping()` ở mỗi `reset`.
- Tia: `p.rayTestBatch(rayFromPositions, rayToPositions)` trả list `(objectUniqueId, linkIndex, hitFraction, hitPosition, hitNormal)`; `objectUniqueId = -1` khi không trúng. 16 tia ngang trong hệ thế giới, điểm đầu cách tâm 0.12 m, dài 4 m; khoảng cách = `0.12 + hitFraction·(4 − 0.12)`.
- Va chạm: `p.getContactPoints(bodyA=droneId)` trả tuple, phần tử `[2]` là id vật B (mặt đất `PLANE_ID` hoặc cột).

## Những điểm khác với HoverAviary gốc
- `HoverAviary` xuất phát ở `INIT_XYZS` mặc định gần mặt đất (z ≈ 0.11) và `info = {"answer": 42}`; ta xuất phát trên không và trả `info` đầy đủ.
- `HoverAviary._computeTruncated` gộp cả "bay xa/nghiêng" lẫn "hết giờ" vào `truncated`; ta coi bay ra ngoài vùng/nghiêng/va chạm là **terminated** (có reward phạt), chỉ hết giờ mới là `truncated` để PPO bootstrap đúng.

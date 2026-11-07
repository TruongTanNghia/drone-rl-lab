# Nhật ký thí nghiệm

Mỗi dòng: ngày · đổi gì · vì sao · kết quả. Mọi thay đổi reward / hyperparameter / curriculum / tham số baseline phải có dòng ở đây.

| Ngày | Giai đoạn | Đổi gì | Vì sao | Kết quả |
|---|---|---|---|---|
| 2026-11-07 | G0 | Dùng Python 3.12 + uv venv thay vì Conda 3.10 | Máy không có Conda; `pyproject.toml` của gym-pybullet-drones main yêu cầu Python ^3.12; PyBullet không có wheel Windows nên build từ sdist bằng MSVC có sẵn | Cài được, `pid.py` của thư viện chạy headless OK |
| 2026-11-07 | G0 | `env.speed_limit` ghi đè SPEED_LIMIT 0.25 m/s của thư viện; G1 = 1.0, G2–G4 = 1.5 m/s | Đo đáp ứng VEL (`docs/calibration.json`): 1.5 m/s cho nghiêng đỉnh 0.70 rad, 2.0 m/s cho 0.86 rad | `max_tilt` G2–G4 đặt 1.2 rad (prompt không quy định cho các giai đoạn này; G1 giữ 0.8 theo prompt) |
| 2026-11-07 | G0 | Hệ số gió `wind_cd = 0.02` | Gió 2 m/s cần gây trôi thấy rõ: 0.02 → trôi 1.09 m sau 6 s khi PID giữ vị trí | Ghi ở `library_notes.md` |
| 2026-11-07 | G0 | Quan sát G4 có 15 trường (prompt ghi 14) | Liệt kê trong prompt: vis,cx,cy,w,h (5) + z−4 (1) + vel (3) + rpy (3) + ang_v (3) = 15 | Giữ đủ 15, ghi rõ ở `perception/encoders.py` |
| 2026-11-07 | G0 | Bay ra ngoài vùng / nghiêng / va chạm → `terminated` (không phải `truncated`) | PPO cần coi đây là trạng thái kết thúc có phạt, không bootstrap giá trị | Chỉ số "số lần bị cắt lượt" vẫn đếm riêng qua `reason` |
| 2026-11-07 | G0 | `SmokeEnv` = bài toán HoverAviary gốc (reward `max(0, 2 − d⁴)`, cắt lượt khi |x|,|y| > 1.5, z > 2, nghiêng > 0.4) trên giao diện 4.1 | Prompt yêu cầu bọc HoverAviary; kế thừa trực tiếp không trả `info` chuẩn được | G0 train 20 480 bước OK |

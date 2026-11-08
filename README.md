# Drone Pilot Trainer — phần mềm huấn luyện học viên lái drone

Học viên cầm **tay cầm USB** (hoặc bàn phím), bay trong **sân tập 3D** theo **giáo trình bài tập**; sau mỗi bài **AI chấm điểm** chuỗi thao tác cần và quỹ đạo bay, chỉ ra lỗi **tay run, gắt cần, over-control, lảo đảo**, và gợi ý bài kế tiếp. Có màn hình giảng viên (chấm thi, quản lý lớp — đang làm).

## Chạy thử
```
cd app/web
npm install
npm run dev          # http://localhost:3000  (máy nào bận cổng 3000: npx next dev -p 3100)
```
Cắm tay cầm USB, bấm một nút bất kỳ để trình duyệt nhận, vào bài và gạt cần. Không có tay cầm: W/S ga, A/D yaw, mũi tên pitch/roll.

## Giáo trình (app/web/src/lib/sim/lessons.ts)
| Bài | Tên | Mục tiêu | Đạt |
|---|---|---|---|
| BT01 | Làm quen tay cầm | làm đủ 4 kênh, bay 5 s, tiếp đất | ≥ 50 |
| BT02 | Cất cánh | lên 1,5 m, giữ 5 s trong 1 m quanh bãi | ≥ 60 |
| BT03 | Giữ vị trí (Hover) | 20 s trong vòng 0,75 m ở 1,5 m | ≥ 60 |
| BT04 | Bay hình vuông | 4 góc cạnh 4 m theo thứ tự | ≥ 60 |
| BT05 | Bay số 8 | 2 vòng tròn bán kính 2,2 m | ≥ 60 |
| BT06 | Hạ cánh | từ 3 m xuống bãi, chạm < 0,8 m/s, lệch < 0,5 m | ≥ 60 |

## AI chấm điểm (app/web/src/lib/sim/grading.ts)
Mẫu 20 Hz: 4 kênh cần + vị trí/vận tốc/góc. Điểm 100 = Điều khiển 25 + Chính xác 25 + Ổn định 25 + Hoàn thành 25.
Cờ lỗi (mỗi cờ kèm số đo làm bằng chứng và lời khuyên):
- **Tay run** — trung vị |sai phân bậc hai| của cần > 0,035 (rung cao tần liên tục).
- **Gắt cần** — tốc độ gạt cần p95 > 4 hành trình/s.
- **Over-control** — > 70 lần đảo cần/phút kèm > 20 dao động vị trí/phút.
- **Lảo đảo** — độ lệch chuẩn góc nghiêng > 7° hoặc dao động liên tục khi cần giữ yên.
- **Giữ độ cao kém**, **Tiếp đất mạnh/lệch**.
Gợi ý bài kế tiếp: bài đầu chưa đạt; nếu một lỗi lặp ≥ 3/5 lượt gần nhất thì khuyên ôn bài liên quan.

## Mô phỏng (app/web/src/lib/sim/drone.ts)
Quadcopter chế độ góc (angle mode) như drone tập lái: cần pitch/roll → góc nghiêng mục tiêu ±30°, yaw → tốc độ quay, ga → lực đẩy quanh mức treo; vật lý 240 Hz trong trình duyệt (không trễ tay). Mô hình 3D Crazyflie 2.x (`app/web/public/models/cf2.glb`). Gió giật tuỳ chọn.

## Cấu trúc
```
app/web/src/lib/sim/     drone.ts (vật lý) · input.ts (tay cầm/bàn phím) · lessons.ts (giáo trình) · grading.ts (AI chấm)
app/web/src/components/  FlightSim.tsx (cảnh Three.js, HUD, bảng kết quả)
app/web/src/app/         / (giáo trình, lịch sử, gợi ý) · /fly/[bài]
```
Lịch sử bay hiện lưu trong trình duyệt (localStorage); bản lớp học sẽ lưu về máy chủ giảng viên.

## Lộ trình
1. ✅ Bản thử nghiệm: bay được, 6 bài, chấm điểm + cờ lỗi, gợi ý.
2. Màn hình giảng viên: danh sách học viên, phát lại chuyến bay, chấm thi, xuất báo cáo.
3. Đóng gói Electron (.exe), hiệu chỉnh tay cầm theo đề cương, mô hình chấm học từ dữ liệu giảng viên.

Code RL (drone tự bay) trước đây nằm ở nhánh `legacy/rl`, không dùng cho sản phẩm này.

// Giáo trình bài tập BT01–BT06 và bộ theo dõi tiến độ từng bài (chạy mỗi khung hình).

import type { DroneState, Inputs, Vec3 } from "./drone";

export type LessonKind = "familiar" | "takeoff" | "hover" | "waypoints" | "landing";

export type Lesson = {
  id: string;
  name: string;
  short: string;
  kind: LessonKind;
  goal: string;
  steps: string[];
  timeLimit: number; // s
  altitude: number; // m mục tiêu
  waypoints?: Vec3[];
  hoverSeconds?: number;
  hoverRadius?: number;
  startAirborne?: boolean;
  wind?: number; // m/s² biên độ gió giật
  passScore: number;
};

export const LESSONS: Lesson[] = [
  {
    id: "BT01", name: "Làm quen tay cầm", short: "Làm quen", kind: "familiar", altitude: 1.5, timeLimit: 180, passScore: 50,
    goal: "Nhận biết 4 kênh điều khiển và cảm giác cần. Không chấm độ chính xác, chỉ cần làm đủ các thao tác.",
    steps: ["Đẩy ga lên để cất cánh, lên quá 0,5 m", "Quay yaw trái rồi phải (cần trái ngang)", "Chúi tới rồi lùi (cần phải dọc)", "Nghiêng trái rồi phải (cần phải ngang)", "Giữ ở trên không 5 giây", "Hạ ga từ từ để tiếp đất"],
  },
  {
    id: "BT02", name: "Cất cánh", short: "Cất cánh", kind: "takeoff", altitude: 1.5, hoverSeconds: 5, timeLimit: 60, passScore: 60,
    goal: "Cất cánh thẳng đứng lên 1,5 m và giữ 5 giây, không trôi ngang quá 1 m.",
    steps: ["Tăng ga đều, không giật", "Lên tới 1,5 m (±0,3 m)", "Giữ 5 giây trong vòng 1 m quanh bãi"],
  },
  {
    id: "BT03", name: "Giữ vị trí (Hover)", short: "Hover", kind: "hover", altitude: 1.5, hoverSeconds: 20, hoverRadius: 0.75, timeLimit: 90, passScore: 60,
    goal: "Treo trong vòng tròn bán kính 0,75 m ở độ cao 1,5 m tổng cộng 20 giây. Chấm độ ổn định và độ mượt cần.",
    steps: ["Cất cánh lên 1,5 m", "Đưa drone vào vòng sáng", "Giữ tổng cộng 20 giây trong vòng (±0,3 m độ cao)"],
  },
  {
    id: "BT04", name: "Bay hình vuông", short: "Hình vuông", kind: "waypoints", altitude: 1.5, timeLimit: 120, passScore: 60,
    waypoints: [{ x: 2, y: 1.5, z: -2 }, { x: 2, y: 1.5, z: 2 }, { x: -2, y: 1.5, z: 2 }, { x: -2, y: 1.5, z: -2 }, { x: 0, y: 1.5, z: 0 }],
    goal: "Bay qua 4 góc hình vuông cạnh 4 m ở độ cao 1,5 m theo thứ tự, rồi về giữa. Giữ hướng mũi cố định.",
    steps: ["Cất cánh lên 1,5 m", "Bay qua từng vòng sáng theo thứ tự (vòng kế tiếp sáng vàng)", "Về vòng cuối ở giữa bãi"],
  },
  {
    id: "BT05", name: "Bay số 8", short: "Số 8", kind: "waypoints", altitude: 1.5, timeLimit: 150, passScore: 60,
    waypoints: (() => {
      const pts: Vec3[] = [];
      const R = 2.2;
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2; // vòng phải, ngược chiều kim đồng hồ nhìn từ trên
        pts.push({ x: R + R * Math.cos(Math.PI + a), y: 1.5, z: -R * Math.sin(Math.PI + a) });
      }
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2; // vòng trái, chiều ngược lại
        pts.push({ x: -R + R * Math.cos(a), y: 1.5, z: R * Math.sin(a) });
      }
      return pts.filter((_, i) => i % 2 === 0).concat([{ x: 0, y: 1.5, z: 0 }]);
    })(),
    goal: "Bay theo quỹ đạo số 8 (hai vòng tròn bán kính 2,2 m) qua các vòng sáng, giữ độ cao 1,5 m.",
    steps: ["Cất cánh lên 1,5 m", "Bay qua các vòng theo thứ tự, phối hợp pitch + roll + yaw", "Về vòng cuối ở giữa"],
  },
  {
    id: "BT06", name: "Hạ cánh", short: "Hạ cánh", kind: "landing", altitude: 3, timeLimit: 60, startAirborne: true, passScore: 60,
    goal: "Từ độ cao 3 m, hạ xuống chính giữa bãi đáp: chạm đất nhẹ (< 0,8 m/s), thăng bằng, trong vòng 0,5 m.",
    steps: ["Giảm ga từ từ, giữ tốc độ hạ < 1 m/s", "Giữ drone trên bãi đáp (vòng sáng)", "Chạm đất nhẹ, cần ga về hết"],
  },
];

export function lessonById(id: string): Lesson | undefined {
  return LESSONS.find((l) => l.id === id);
}

// ---------------------------------------------------------------- theo dõi tiến độ

export type Progress = {
  status: "running" | "done" | "failed";
  reason: string;
  instruction: string;
  checklist: { text: string; done: boolean }[];
  fraction: number; // 0..1
  target: Vec3 | null; // điểm cần tới (vẽ vòng)
  nextTarget: Vec3 | null;
  wpIndex: number;
  hoverTime: number;
  inZone: boolean;
};

export type Sample = { t: number; u: Inputs; pos: Vec3; vel: Vec3; roll: number; pitch: number; yaw: number; inZone: boolean };

export function createTracker(lesson: Lesson) {
  const done = new Set<string>();
  let hoverTime = 0;
  let wp = 0;
  let airborneTime = 0;
  let stepsDone = lesson.steps.map(() => false);
  let yawMin = 0, yawMax = 0, pitchMin = 0, pitchMax = 0, rollMin = 0, rollMax = 0, maxAlt = 0;
  let status: Progress["status"] = "running";
  let reason = "";

  function dist2(a: Vec3, b: Vec3) {
    return Math.hypot(a.x - b.x, a.z - b.z);
  }

  function update(s: DroneState, u: Inputs, dt: number): Progress {
    const pad = { x: 0, y: lesson.altitude, z: 0 };
    let instruction = "";
    let target: Vec3 | null = null;
    let nextTarget: Vec3 | null = null;
    let inZone = false;
    maxAlt = Math.max(maxAlt, s.pos.y);
    if (!s.onGround) airborneTime += dt;

    if (status === "running" && s.crashed) {
      status = "failed";
      reason = `Rơi: ${s.crashReason}`;
    }
    if (status === "running" && s.t > lesson.timeLimit) {
      status = "failed";
      reason = `Hết ${lesson.timeLimit} s`;
    }

    switch (lesson.kind) {
      case "familiar": {
        yawMin = Math.min(yawMin, u.yaw); yawMax = Math.max(yawMax, u.yaw);
        pitchMin = Math.min(pitchMin, u.pitch); pitchMax = Math.max(pitchMax, u.pitch);
        rollMin = Math.min(rollMin, u.roll); rollMax = Math.max(rollMax, u.roll);
        if (maxAlt > 0.5) done.add("alt");
        if (yawMin < -0.4 && yawMax > 0.4) done.add("yaw");
        if (pitchMin < -0.4 && pitchMax > 0.4) done.add("pitch");
        if (rollMin < -0.4 && rollMax > 0.4) done.add("roll");
        if (airborneTime > 5) done.add("air");
        if (done.has("alt") && s.onGround && s.landings > 0) done.add("land");
        stepsDone = ["alt", "yaw", "pitch", "roll", "air", "land"].map((k) => done.has(k));
        const nxt = lesson.steps.findIndex((_, i) => !stepsDone[i]);
        instruction = nxt < 0 ? "Hoàn thành!" : lesson.steps[nxt];
        if (status === "running" && nxt < 0) status = "done";
        break;
      }
      case "takeoff": {
        target = pad;
        const dAlt = Math.abs(s.pos.y - lesson.altitude);
        const dH = dist2(s.pos, pad);
        inZone = !s.onGround && dAlt <= 0.3 && dH <= 1.0;
        if (!s.onGround) done.add("lift");
        if (inZone) hoverTime += dt;
        else if (hoverTime > 0 && !inZone) hoverTime = Math.max(0, hoverTime - dt * 0.5); // rời vùng thì trừ dần
        stepsDone = [done.has("lift"), dAlt <= 0.3 && !s.onGround, hoverTime >= (lesson.hoverSeconds ?? 5)];
        instruction = s.onGround ? "Tăng ga đều để cất cánh" : dAlt > 0.3 ? (s.pos.y < lesson.altitude ? "Lên tiếp tới 1,5 m" : "Cao quá, hạ ga nhẹ") : `Giữ ${Math.max(0, (lesson.hoverSeconds ?? 5) - hoverTime).toFixed(1)} s nữa`;
        if (status === "running" && hoverTime >= (lesson.hoverSeconds ?? 5)) status = "done";
        break;
      }
      case "hover": {
        target = pad;
        const dAlt = Math.abs(s.pos.y - lesson.altitude);
        const dH = dist2(s.pos, pad);
        inZone = !s.onGround && dAlt <= 0.3 && dH <= (lesson.hoverRadius ?? 0.75);
        if (!s.onGround) done.add("lift");
        if (inZone) {
          hoverTime += dt;
          done.add("enter");
        }
        const need = lesson.hoverSeconds ?? 20;
        stepsDone = [done.has("lift"), done.has("enter"), hoverTime >= need];
        instruction = s.onGround ? "Cất cánh lên 1,5 m" : !inZone ? (dH > (lesson.hoverRadius ?? 0.75) ? "Đưa drone vào vòng sáng" : s.pos.y < lesson.altitude ? "Lên thêm một chút" : "Hạ thấp một chút") : `Giữ yên — còn ${Math.max(0, need - hoverTime).toFixed(1)} s`;
        if (status === "running" && hoverTime >= need) status = "done";
        break;
      }
      case "waypoints": {
        const wps = lesson.waypoints ?? [];
        if (wp < wps.length) {
          target = wps[wp];
          nextTarget = wps[wp + 1] ?? null;
          const d3 = Math.hypot(s.pos.x - target.x, s.pos.y - target.y, s.pos.z - target.z);
          inZone = d3 <= 0.8;
          if (inZone && !s.onGround) wp += 1;
        }
        if (!s.onGround) done.add("lift");
        stepsDone = [done.has("lift"), wp >= wps.length - 1 && wps.length > 0, wp >= wps.length];
        instruction = s.onGround && wp === 0 ? "Cất cánh lên 1,5 m" : wp < wps.length ? `Bay tới vòng ${wp + 1}/${wps.length}` : "Hoàn thành!";
        if (status === "running" && wp >= wps.length) status = "done";
        break;
      }
      case "landing": {
        target = { x: 0, y: 0.03, z: 0 };
        const dH = dist2(s.pos, target);
        inZone = dH <= 0.5;
        stepsDone = [s.vel.y > -1.0 || s.onGround, inZone, s.onGround && s.landings > 0];
        instruction = s.onGround ? "Đã tiếp đất" : s.vel.y < -1.0 ? "Hạ chậm lại!" : dH > 0.5 ? "Đưa drone về trên bãi đáp" : "Hạ ga từ từ, giữ thăng bằng";
        if (status === "running" && s.onGround && s.landings > 0) {
          if (dH > 0.5) {
            status = "failed";
            reason = `Tiếp đất lệch bãi ${dH.toFixed(2)} m`;
          } else if (s.touchdownSpeed > 0.8) {
            status = "failed";
            reason = `Tiếp đất mạnh ${s.touchdownSpeed.toFixed(2)} m/s (cần < 0,8)`;
          } else status = "done";
        }
        break;
      }
    }

    const fraction = lesson.kind === "waypoints" ? (lesson.waypoints?.length ? wp / lesson.waypoints.length : 0) : lesson.kind === "hover" || lesson.kind === "takeoff" ? Math.min(1, hoverTime / (lesson.hoverSeconds ?? 1)) : stepsDone.filter(Boolean).length / stepsDone.length;
    return { status, reason, instruction, checklist: lesson.steps.map((text, i) => ({ text, done: stepsDone[i] ?? false })), fraction, target, nextTarget, wpIndex: wp, hoverTime, inZone };
  }

  return { update };
}

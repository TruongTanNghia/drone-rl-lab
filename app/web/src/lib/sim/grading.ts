// AI chấm điểm chuyến bay: trích đặc trưng từ chuỗi cần điều khiển + trạng thái drone,
// phát hiện lỗi thao tác (tay run, gắt cần, over-control, lảo đảo), cho điểm 4 phần và gợi ý.
// Phiên bản 1: luật + ngưỡng đo được, mọi cờ đều kèm bằng chứng số. (Sau này thay bằng mô hình học từ dữ liệu giảng viên chấm.)

import type { Lesson, Progress, Sample } from "./lessons";

export type Flag = { code: "tay_run" | "gat_can" | "over_control" | "lao_dao" | "cao_do" | "tiep_dat"; name: string; severity: 1 | 2 | 3; evidence: string; tip: string };

export type Report = {
  lessonId: string;
  date: string;
  duration: number;
  status: Progress["status"];
  reason: string;
  score: number; // 0..100
  parts: { control: number; accuracy: number; stability: number; completion: number }; // mỗi phần 0..25
  flags: Flag[];
  features: Record<string, number>;
  tips: string[];
};

function std(a: number[]): number {
  if (a.length < 2) return 0;
  const m = a.reduce((x, y) => x + y, 0) / a.length;
  return Math.sqrt(a.reduce((x, y) => x + (y - m) * (y - m), 0) / (a.length - 1));
}
function pct(a: number[], p: number): number {
  if (!a.length) return 0;
  const s = [...a].sort((x, y) => x - y);
  return s[Math.min(s.length - 1, Math.floor(p * s.length))];
}
function zeroCrossings(a: number[]): number {
  let n = 0;
  for (let i = 1; i < a.length; i++) if ((a[i - 1] < 0 && a[i] > 0) || (a[i - 1] > 0 && a[i] < 0)) n++;
  return n;
}
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

export function grade(lesson: Lesson, samples: Sample[], prog: Progress, extra: { touchdown?: number } = {}): Report {
  const n = samples.length;
  const dt = n > 1 ? (samples[n - 1].t - samples[0].t) / (n - 1) : 0.05;
  const hz = dt > 0 ? 1 / dt : 20;
  const air = samples.filter((s) => s.pos.y > 0.1);
  const f: Record<string, number> = {};
  const flags: Flag[] = [];
  f.touchdown = +(extra.touchdown ?? 0).toFixed(2);

  // --- đặc trưng cần điều khiển (chỉ khi đang bay)
  const chans = ["thr", "yaw", "pitch", "roll"] as const;
  let jitterMax = 0, rateP95Max = 0, reversalsPerMin = 0;
  for (const c of chans) {
    const x = air.map((s) => s.u[c]);
    if (x.length < hz) continue;
    const rate = x.slice(1).map((v, i) => Math.abs(v - x[i]) / dt); // đơn vị cần / s
    const p95 = pct(rate, 0.95);
    rateP95Max = Math.max(rateP95Max, p95);
    // tay run = rung cao tần liên tục: trung vị |sai phân bậc hai| (không bắt chuyển động nhanh nhưng mượt, không bắt gạt đơn lẻ)
    const d2 = x.slice(2).map((v, i) => Math.abs(v - 2 * x[i + 1] + x[i]));
    const jitter = pct(d2, 0.5);
    jitterMax = Math.max(jitterMax, jitter);
    if (c === "pitch" || c === "roll") {
      const d = x.slice(1).map((v, i) => v - x[i]).filter((v) => Math.abs(v) > 0.02);
      reversalsPerMin = Math.max(reversalsPerMin, (zeroCrossings(d) / (x.length * dt)) * 60);
    }
    f[`rate95_${c}`] = +p95.toFixed(2);
    f[`jitter_${c}`] = +jitter.toFixed(3);
  }
  f.reversals_per_min = +reversalsPerMin.toFixed(0);

  // --- đặc trưng trạng thái bay
  const tiltDeg = air.map((s) => (Math.acos(Math.cos(s.roll) * Math.cos(s.pitch)) * 180) / Math.PI);
  const vh = air.map((s) => Math.hypot(s.vel.x, s.vel.z));
  const altErr = air.map((s) => Math.abs(s.pos.y - lesson.altitude));
  f.tilt_std = +std(tiltDeg).toFixed(1);
  f.vh_mean = +(vh.reduce((a, b) => a + b, 0) / Math.max(1, vh.length)).toFixed(2);
  f.alt_err_mean = +(altErr.reduce((a, b) => a + b, 0) / Math.max(1, altErr.length)).toFixed(2);
  // lảo đảo: vận tốc ngang đổi dấu liên tục (dao động quanh một điểm) khi đang cố giữ yên
  const vx = air.map((s) => s.vel.x), vz = air.map((s) => s.vel.z);
  const osc = air.length > hz * 3 ? ((zeroCrossings(vx) + zeroCrossings(vz)) / 2 / (air.length * dt)) * 60 : 0;
  f.oscillations_per_min = +osc.toFixed(0);
  const inZoneFrac = air.length ? air.filter((s) => s.inZone).length / air.length : 0;
  f.in_zone_frac = +inZoneFrac.toFixed(2);
  const duration = n ? samples[n - 1].t : 0;
  f.duration = +duration.toFixed(1);

  // --- cờ lỗi thao tác
  if (jitterMax > 0.035) flags.push({ code: "tay_run", name: "Tay run", severity: jitterMax > 0.1 ? 3 : jitterMax > 0.06 ? 2 : 1, evidence: `rung cao tần của cần = ${jitterMax.toFixed(3)} (ngưỡng 0,035)`, tip: "Tì nhẹ ngón cái vào cần, thở đều; tập giữ cần ở một điểm 10 giây." });
  if (rateP95Max > 4.0) flags.push({ code: "gat_can", name: "Gắt cần", severity: rateP95Max > 9 ? 3 : rateP95Max > 6 ? 2 : 1, evidence: `tốc độ gạt cần p95 = ${rateP95Max.toFixed(1)} hành trình/s (ngưỡng 4,0)`, tip: "Đẩy cần theo nửa hành trình, đợi drone đáp ứng ~0,3 s rồi mới sửa tiếp." });
  if (reversalsPerMin > 70 && osc > 20) flags.push({ code: "over_control", name: "Over-control", severity: reversalsPerMin > 140 ? 3 : reversalsPerMin > 100 ? 2 : 1, evidence: `${reversalsPerMin.toFixed(0)} lần đảo cần/phút kèm ${osc.toFixed(0)} dao động/phút`, tip: "Sửa ít hơn: khi drone trôi, đưa cần nhẹ về phía ngược lại rồi thả về giữa, đừng chờ nó dừng hẳn mới thả." });
  if (f.tilt_std > 7 || (osc > 25 && lesson.kind !== "waypoints")) flags.push({ code: "lao_dao", name: "Lảo đảo", severity: f.tilt_std > 12 ? 3 : f.tilt_std > 9 ? 2 : 1, evidence: `độ lệch chuẩn góc nghiêng ${f.tilt_std}° · ${osc.toFixed(0)} dao động/phút`, tip: "Giữ cần phải gần giữa, chỉ nhích rất nhỏ; nhìn vào thân drone chứ không nhìn cần." });
  if (lesson.kind !== "landing" && lesson.kind !== "familiar" && f.alt_err_mean > 0.5) flags.push({ code: "cao_do", name: "Giữ độ cao kém", severity: f.alt_err_mean > 1.0 ? 2 : 1, evidence: `sai số độ cao trung bình ${f.alt_err_mean} m`, tip: "Ga là kênh chậm: chỉnh ga từng chút, đợi 1 giây xem độ cao đổi thế nào." });
  const last = samples[n - 1];
  if (lesson.kind === "landing" && last && prog.status === "failed" && prog.reason.includes("Tiếp đất")) flags.push({ code: "tiep_dat", name: "Tiếp đất mạnh/lệch", severity: 2, evidence: prog.reason, tip: "Giảm ga xuống dưới giữa một chút để hạ ~0,5 m/s; ở 0,3 m cuối hãy hạ ga thêm." });

  // --- điểm 4 phần (0–25 mỗi phần)
  const control = clamp(25 - 120 * Math.max(0, jitterMax - 0.025) - 1.6 * Math.max(0, rateP95Max - 3) - 0.05 * Math.max(0, reversalsPerMin - 60), 0, 25);
  const stability = clamp(25 - 1.2 * Math.max(0, f.tilt_std - 4) - 0.25 * Math.max(0, osc - 12), 0, 25);
  let accuracy: number;
  switch (lesson.kind) {
    case "hover":
    case "takeoff":
      accuracy = clamp(25 * inZoneFrac * (1 - Math.min(1, f.alt_err_mean / 1.5)) + 5, 0, 25);
      break;
    case "waypoints":
      accuracy = clamp(25 * prog.fraction * (1 - Math.min(0.6, f.alt_err_mean / 2)), 0, 25);
      break;
    case "landing":
      accuracy = last ? clamp(25 - 20 * Math.min(1, Math.hypot(last.pos.x, last.pos.z) / 0.8) - 8 * Math.max(0, (f.touchdown ?? 0) - 0.5), 0, 25) : 0;
      break;
    default:
      accuracy = 20;
  }
  let completion: number;
  if (prog.status === "done") completion = clamp(25 - 5 * Math.max(0, duration / lesson.timeLimit - 0.6), 15, 25);
  else if (prog.status === "failed" && prog.reason.startsWith("Rơi")) completion = 0;
  else completion = clamp(20 * prog.fraction, 0, 20);

  const parts = { control: +control.toFixed(1), accuracy: +accuracy.toFixed(1), stability: +stability.toFixed(1), completion: +completion.toFixed(1) };
  const score = Math.round(parts.control + parts.accuracy + parts.stability + parts.completion);
  const tips = flags.sort((a, b) => b.severity - a.severity).map((x) => x.tip);
  if (!flags.length && prog.status === "done") tips.push("Bay sạch. Sang bài tiếp theo hoặc bật gió để tăng độ khó.");
  if (prog.status === "failed" && prog.reason.startsWith("Rơi")) tips.unshift("Khi mất kiểm soát: thả hai cần về giữa, drone tự cân bằng, rồi chỉnh ga.");

  return { lessonId: lesson.id, date: new Date().toISOString(), duration: +duration.toFixed(1), status: prog.status, reason: prog.reason, score, parts, flags, features: f, tips };
}

// ---------------------------------------------------------------- lưu lịch sử học viên (localStorage; sau này là CSDL lớp học)
const KEY = "drone-trainer.attempts";
export type Attempt = Pick<Report, "lessonId" | "date" | "duration" | "status" | "score" | "parts" | "reason"> & { flags: { code: Flag["code"]; name: string; severity: number }[] };

export function loadAttempts(): Attempt[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}
export function saveAttempt(r: Report) {
  try {
    const a = loadAttempts();
    a.push({ lessonId: r.lessonId, date: r.date, duration: r.duration, status: r.status, score: r.score, parts: r.parts, reason: r.reason, flags: r.flags.map((x) => ({ code: x.code, name: x.name, severity: x.severity })) });
    localStorage.setItem(KEY, JSON.stringify(a.slice(-500)));
  } catch {
    /* bỏ qua */
  }
}

/** Gợi ý bài tiếp theo (cá nhân hóa đơn giản): bài đầu tiên chưa đạt; nếu lỗi lặp lại thì khuyên ôn bài liên quan. */
export function recommend(attempts: Attempt[], lessons: Lesson[]): { lessonId: string; why: string } {
  const best = (id: string) => Math.max(0, ...attempts.filter((a) => a.lessonId === id).map((a) => a.score));
  const recent = attempts.slice(-5);
  const count = (code: string) => recent.reduce((n, a) => n + (a.flags.some((f) => f.code === code) ? 1 : 0), 0);
  if (count("lao_dao") >= 3 || count("over_control") >= 3) return { lessonId: "BT03", why: "Lỗi lảo đảo/over-control lặp lại ở 3/5 lần gần nhất → ôn lại Hover để tập sửa cần nhỏ." };
  if (count("gat_can") >= 3 || count("tay_run") >= 3) return { lessonId: "BT01", why: "Cần gắt/tay run lặp lại → quay về bài làm quen, tập cảm giác cần." };
  for (const l of lessons) if (best(l.id) < l.passScore) return { lessonId: l.id, why: best(l.id) === 0 ? "Bài chưa làm." : `Điểm cao nhất ${best(l.id)} < ${l.passScore} điểm đạt.` };
  return { lessonId: lessons[lessons.length - 1].id, why: "Đã đạt mọi bài. Tập lại với gió để nâng cao." };
}

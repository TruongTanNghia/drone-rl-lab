// Kiểu dữ liệu + hàm gọi FastAPI (qua rewrite /api/* trong next.config.ts). Không có dữ liệu mẫu.

export type Gate = { name: string; rule: string; value: number | null; passed: boolean; extra?: string[] };

export type EvalSummary = {
  tag: string;
  controller: string;
  source: string | null;
  n_episodes: number;
  metrics: Record<string, number | null>;
  gate: Gate;
  created_at: string;
  file: string;
  seeds: number[];
};

export type Progress = {
  timesteps: number;
  total_steps: number;
  ep_rew_mean: number | null;
  ep_len_mean: number | null;
  success_rate: number | null;
  wall_time: number | null;
  stage: string | null;
  log_mtime: number;
  file: string;
};

export type RunStatus = "đã huấn luyện" | "đang huấn luyện" | "chưa có log";

export type RunSummary = {
  run_id: string;
  phase: string;
  algo: string;
  train_seed: number;
  created: string;
  gate_rule: { name: string; metric: string; op: string; value: number; extra: string[] } | null;
  has_model: boolean;
  has_curve: boolean;
  train_meta: Record<string, string | number> | null;
  status: RunStatus;
  progress: Progress | null;
  evals: EvalSummary[];
  files: { config: string; train_log: string; train_meta: string };
};

export type RunDetail = RunSummary & {
  config: Record<string, unknown>;
  curriculum: { timesteps: number; from: string; to: string; success_rate: number }[];
};

export type CurveRow = { timesteps: number; ep_rew_mean: number | null; ep_len_mean: number | null; success_rate: number | null; wall_time: number | null; stage: string | null };

export type RoadmapItem = {
  phase: string;
  n_runs: number;
  status: "chưa chạy" | "chưa đánh giá" | "đạt" | "chưa đạt";
  gates: { run_id: string; tag: string; passed: boolean; value: number | null; rule: string; file: string }[];
};

export type MetricsDoc = {
  schema: string;
  run_id: string;
  phase: string;
  controller: string;
  source: string | null;
  train_seed: number | null;
  config_hash: string;
  git_commit: string;
  created_at: string;
  eval_seeds: [number, number];
  n_episodes: number;
  metrics: Record<string, number | null>;
  gate: Gate;
  episodes: Record<string, unknown>[];
  file: string;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, msg: string) {
    super(msg);
    this.status = status;
  }
}

export async function api<T>(path: string): Promise<T> {
  const r = await fetch(path, { cache: "no-store" });
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(r.status, detail);
  }
  return (await r.json()) as T;
}

export const PHASES = ["g0", "g1", "g2", "g3", "g4", "g5"] as const;

export const PHASE_TITLES: Record<string, string> = {
  g0: "Bộ khung chuẩn",
  g1: "Giữ độ cao",
  g2: "Bay theo điểm, có gió",
  g3: "Né vật cản",
  g4: "Tìm và bám mục tiêu",
  g5: "Demo và báo cáo",
};

export const PHASE_BLURB: Record<string, string> = {
  g0: "Môi trường, giao diện, test chống làm giả, viewer mở được quỹ đạo.",
  g1: "HoverTask: xuất phát ngẫu nhiên, giữ tại (0, 0, 1) m. PPO so với PID.",
  g2: "WaypointTask: gió OU + đổi khối lượng, curriculum 1 điểm → nhiều điểm.",
  g3: "ObstacleTask: 9 cột, 16 tia laser, bản đồ có kiểm tra BFS.",
  g4: "TargetTask: camera nhìn xuống, khung YOLO/sim thay vì toạ độ thật.",
  g5: "Video mỗi giai đoạn, dashboard, báo cáo cuối có nguồn gốc số liệu.",
};

// Ngưỡng cổng theo configs/*.yaml (đặc tả, không phải kết quả). Khi có run thì rule thật đọc từ metrics.json.
export const GATE_SPEC: Record<string, string> = {
  g0: "n_episodes ≥ 5 · pytest xanh · viewer mở được",
  g1: "mean_pos_err_after_settle < 0.1 m · không rơi ở cả 3 seed",
  g2: "success_rate ≥ 0.90 trên 100 lượt",
  g3: "success_rate ≥ 0.85 trên 100 lượt",
  g4: "in_frame_frac ≥ 0.80 trên 100 lượt",
  g5: "video + report_final.md + mọi số có nguồn",
};

export const METRIC_LABELS: Record<string, string> = {
  success_rate: "tỷ lệ đạt",
  mean_pos_err_after_settle: "sai số TB sau 3 s (m)",
  truncation_count: "cắt lượt",
  crash_count: "rơi",
  collision_count: "va chạm",
  mean_return: "return TB",
  mean_ep_len: "độ dài lượt TB",
  mean_finish_time: "thời gian xong TB (s)",
  mean_reached: "số điểm chạm TB",
  mean_min_clearance: "khoảng hở nhỏ nhất TB (m)",
  in_frame_frac: "mục tiêu trong khung",
  visible_frac: "khung nhìn thấy",
  mean_final_offset: "lệch cuối (m)",
};

export const PHASE_METRICS: Record<string, string[]> = {
  g0: ["mean_pos_err_after_settle", "truncation_count", "crash_count", "success_rate", "mean_return"],
  g1: ["mean_pos_err_after_settle", "truncation_count", "crash_count", "success_rate", "mean_return"],
  g2: ["success_rate", "mean_finish_time", "mean_reached", "crash_count", "mean_return"],
  g3: ["success_rate", "collision_count", "mean_finish_time", "mean_min_clearance", "mean_return"],
  g4: ["in_frame_frac", "visible_frac", "crash_count", "mean_final_offset", "mean_return"],
};

export const CONTROLLER_NAMES: Record<string, string> = { ppo: "PPO", sac: "SAC", pid: "PIDBaseline", apf: "APFBaseline", bbox: "BBoxServoBaseline", random: "Random" };

export function fmt(v: number | null | undefined, d = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(d);
}

export function fmtSteps(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}k`;
  return String(v);
}

export function fmtDur(sec: number | null | undefined): string {
  if (sec === null || sec === undefined || Number.isNaN(sec)) return "—";
  const s = Math.round(sec);
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} ph ${s % 60} s`;
  return `${Math.floor(m / 60)} h ${m % 60} ph`;
}

export function isTraining(r: RunSummary): boolean {
  return r.status === "đang huấn luyện";
}

/** Ước tính thời gian còn lại từ tốc độ trung bình của chính run đó (timesteps / wall_time). */
export function etaSec(p: Progress | null): number | null {
  if (!p || !p.wall_time || !p.timesteps || !p.total_steps) return null;
  const rate = p.timesteps / p.wall_time;
  return Math.max(0, (p.total_steps - p.timesteps) / rate);
}

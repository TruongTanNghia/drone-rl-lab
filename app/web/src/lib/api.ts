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

export const PHASE_TITLES: Record<string, string> = {
  g0: "Bộ khung chuẩn",
  g1: "Giữ độ cao",
  g2: "Bay theo điểm, có gió",
  g3: "Né vật cản",
  g4: "Tìm và bám mục tiêu (RL + DL)",
  g5: "Demo và báo cáo",
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

export function fmt(v: number | null | undefined, d = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(d);
}

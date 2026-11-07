"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import LearningCurve from "@/components/LearningCurve";
import MetricsTable from "@/components/MetricsTable";
import Provenance from "@/components/Provenance";
import ViewerFrame from "@/components/ViewerFrame";
import { api, ApiError, fmt, PHASE_TITLES, type CurveRow, type RunDetail } from "@/lib/api";

export default function RunDetailView({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [curve, setCurve] = useState<{ rows: CurveRow[]; file: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tag, setTag] = useState<string>("");
  const [seed, setSeed] = useState<number | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<"all" | "fail" | "ok">("all");
  const [episodes, setEpisodes] = useState<Record<string, unknown>[]>([]);

  useEffect(() => {
    api<RunDetail>(`/api/runs/${runId}`)
      .then((r) => {
        setRun(r);
        const first = r.evals.find((e) => e.controller === r.algo) ?? r.evals[0];
        if (first) {
          setTag(first.tag);
          setSeed(first.seeds[0] ?? null);
        }
      })
      .catch((e: unknown) => setErr(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
    api<{ rows: CurveRow[]; file: string }>(`/api/runs/${runId}/curve`)
      .then(setCurve)
      .catch(() => setCurve({ rows: [], file: "" }));
  }, [runId]);

  useEffect(() => {
    if (!tag) return;
    api<{ episodes: Record<string, unknown>[] }>(`/api/runs/${runId}/eval/${tag}/metrics`)
      .then((m) => setEpisodes(m.episodes ?? []))
      .catch(() => setEpisodes([]));
  }, [runId, tag]);

  const ev = useMemo(() => run?.evals.find((e) => e.tag === tag) ?? null, [run, tag]);
  const seedRows = useMemo(() => {
    const rows = episodes as { seed: number; success: boolean; crashed: boolean; reason: string; return: number }[];
    if (outcomeFilter === "fail") return rows.filter((r) => r.crashed || !r.success);
    if (outcomeFilter === "ok") return rows.filter((r) => r.success && !r.crashed);
    return rows;
  }, [episodes, outcomeFilter]);

  if (err)
    return (
      <div className="card p-5 text-bad">
        {err} — <Link href="/">về lộ trình</Link>
      </div>
    );
  if (!run) return <div className="text-mut">Đang đọc run…</div>;

  const tm = run.train_meta ?? {};
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-baseline gap-3 flex-wrap">
        <Link href="/" className="text-mut text-sm">
          ← lộ trình
        </Link>
        <h1 className="text-xl font-semibold mono">{run.run_id}</h1>
        <span className="badge badge-mut">{run.phase.toUpperCase()} · {PHASE_TITLES[run.phase]}</span>
        <span className="text-mut text-sm">
          {run.algo.toUpperCase()} · seed train {run.train_seed} · cấu hình <span className="mono">{run.files.config}</span>
        </span>
      </div>

      <section className="card p-4">
        <h2 className="font-semibold mb-2">Huấn luyện</h2>
        <div className="flex gap-6 flex-wrap text-sm mb-3">
          <span>
            bước: <Provenance runId={run.run_id} file={run.files.train_meta}><b className="mono">{String(tm.timesteps_done ?? "—")}</b></Provenance>
          </span>
          <span>
            thời gian: <Provenance runId={run.run_id} file={run.files.train_meta}><b className="mono">{tm.wall_time_sec !== undefined ? `${fmt(Number(tm.wall_time_sec), 0)} s` : "—"}</b></Provenance>
          </span>
          <span>
            bước/s: <Provenance runId={run.run_id} file={run.files.train_meta}><b className="mono">{String(tm.steps_per_sec ?? "—")}</b></Provenance>
          </span>
          <span>
            n_envs: <Provenance runId={run.run_id} file={run.files.train_meta}><b className="mono">{String(tm.n_envs ?? "—")}</b></Provenance>
          </span>
          <span>
            commit: <span className="mono text-mut">{String(tm.git_commit ?? "—").slice(0, 10)}</span>
          </span>
          {run.curriculum.length > 0 && (
            <span>
              curriculum: {run.curriculum.map((c) => (
                <span key={c.timesteps} className="mono text-warn">
                  {c.from}→{c.to} @ {c.timesteps}{" "}
                </span>
              ))}
            </span>
          )}
        </div>
        <Provenance runId={run.run_id} file={curve?.file || run.files.train_log}>
          <span className="text-xs text-mut">biểu đồ từ train_log.csv</span>
        </Provenance>
        {curve ? <LearningCurve rows={curve.rows} curriculum={run.curriculum} /> : <div className="text-mut">đang đọc train_log.csv…</div>}
      </section>

      <section className="card p-4">
        <h2 className="font-semibold mb-2">Policy so với baseline</h2>
        <MetricsTable runId={run.run_id} phase={run.phase} evals={run.evals} />
      </section>

      <section className="card p-4">
        <div className="flex items-center gap-3 flex-wrap mb-3">
          <h2 className="font-semibold">Phát lại 3D</h2>
          <select value={tag} onChange={(e) => { setTag(e.target.value); const t = run.evals.find((x) => x.tag === e.target.value); setSeed(t?.seeds[0] ?? null); }} className="bg-bg border border-line rounded px-2 py-1">
            {run.evals.map((e) => (
              <option key={e.tag} value={e.tag}>
                {e.tag} ({e.seeds.length} quỹ đạo)
              </option>
            ))}
          </select>
          <select value={outcomeFilter} onChange={(e) => setOutcomeFilter(e.target.value as "all" | "fail" | "ok")} className="bg-bg border border-line rounded px-2 py-1">
            <option value="all">mọi lượt</option>
            <option value="ok">chỉ lượt thành công</option>
            <option value="fail">chỉ lượt thất bại</option>
          </select>
          <select value={seed ?? ""} onChange={(e) => setSeed(Number(e.target.value))} className="bg-bg border border-line rounded px-2 py-1 mono">
            {(seedRows.length ? seedRows.map((r) => r.seed) : ev?.seeds ?? []).map((s) => {
              const r = (episodes as { seed: number; success: boolean; crashed: boolean; reason: string }[]).find((x) => x.seed === s);
              const mark = r ? (r.crashed ? `✘ ${r.reason}` : r.success ? "✔" : "⏱") : "";
              return (
                <option key={s} value={s}>
                  seed {s} {mark}
                </option>
              );
            })}
          </select>
          {ev && seed !== null && (
            <span className="text-xs text-mut mono">
              file: results/{run.run_id}/eval/{tag}/traj_{seed}.json
            </span>
          )}
        </div>
        {ev ? <ViewerFrame runId={run.run_id} tag={tag} seed={seed} /> : <div className="text-mut">Chưa có quỹ đạo để phát.</div>}
      </section>
    </div>
  );
}

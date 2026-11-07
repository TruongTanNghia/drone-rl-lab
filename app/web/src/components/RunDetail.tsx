"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import LearningCurve from "@/components/LearningCurve";
import LiveTraining from "@/components/LiveTraining";
import MetricsTable from "@/components/MetricsTable";
import Provenance from "@/components/Provenance";
import TrainingTimeline from "@/components/TrainingTimeline";
import ViewerFrame, { viewerUrl } from "@/components/ViewerFrame";
import { api, ApiError, fmt, fmtDur, fmtSteps, isTraining, PHASE_BLURB, PHASE_TITLES, type CurveRow, type RunDetail } from "@/lib/api";

type Ep = { seed: number; success: boolean; crashed: boolean; reason: string; return: number };

export default function RunDetailView({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [curve, setCurve] = useState<{ rows: CurveRow[]; file: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tag, setTag] = useState<string>("");
  const [seed, setSeed] = useState<number | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<"all" | "fail" | "ok">("all");
  const [episodes, setEpisodes] = useState<Ep[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    api<RunDetail>(`/api/runs/${runId}`)
      .then((r) => {
        if (!alive) return;
        setRun(r);
        if (!tag) {
          const first = r.evals.find((e) => e.controller === r.algo) ?? r.evals[0];
          if (first) {
            setTag(first.tag);
            setSeed(first.seeds[0] ?? null);
          }
        }
      })
      .catch((e: unknown) => alive && setErr(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
    api<{ rows: CurveRow[]; file: string }>(`/api/runs/${runId}/curve`)
      .then((c) => alive && setCurve(c))
      .catch(() => alive && setCurve({ rows: [], file: "" }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, tick]);

  // run đang train: làm mới mỗi 8 s
  const live = run ? isTraining(run) : false;
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => setTick((t) => t + 1), 8000);
    return () => clearInterval(id);
  }, [live]);

  useEffect(() => {
    if (!tag) return;
    api<{ episodes: Ep[] }>(`/api/runs/${runId}/eval/${tag}/metrics`)
      .then((m) => setEpisodes(m.episodes ?? []))
      .catch(() => setEpisodes([]));
  }, [runId, tag]);

  const ev = useMemo(() => run?.evals.find((e) => e.tag === tag) ?? null, [run, tag]);
  const seedRows = useMemo(() => {
    if (outcomeFilter === "fail") return episodes.filter((r) => r.crashed || !r.success);
    if (outcomeFilter === "ok") return episodes.filter((r) => r.success && !r.crashed);
    return episodes;
  }, [episodes, outcomeFilter]);
  const epStats = useMemo(() => {
    const n = episodes.length;
    if (!n) return null;
    return { n, ok: episodes.filter((e) => e.success && !e.crashed).length, crash: episodes.filter((e) => e.crashed).length };
  }, [episodes]);

  if (err)
    return (
      <div className="panel p-6 text-bad reveal">
        <div className="eyebrow mb-2">Lỗi</div>
        {err} — <Link href="/">về lộ trình</Link>
      </div>
    );
  if (!run) return <div className="text-mut mono text-[12.5px]">Đang đọc run…</div>;

  const tm = run.train_meta ?? {};
  const pol = run.evals.find((e) => e.controller === run.algo);
  const algoCfg = (run.config.algo ?? {}) as Record<string, unknown>;
  const envCfg = (run.config.env ?? {}) as Record<string, unknown>;

  return (
    <div className="flex flex-col gap-6">
      {/* ── thẻ bay ── */}
      <section className="reveal">
        <Link href="/" className="eyebrow hover:text-txt">
          ← lộ trình
        </Link>
        <div className="mt-2 grid gap-6 items-end" style={{ gridTemplateColumns: "minmax(0, 1fr) auto" }}>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="chip chip-acc">
                {run.phase.toUpperCase()} · {PHASE_TITLES[run.phase]}
              </span>
              <span className="chip">
                {run.algo.toUpperCase()} · seed train {run.train_seed}
              </span>
              {live ? (
                <span className="chip chip-acc">
                  <span className="lamp lamp-acc" /> đang huấn luyện
                </span>
              ) : run.status === "đã dừng" ? (
                <span className="chip chip-bad">đã dừng giữa chừng</span>
              ) : pol ? (
                <span className={`stamp ${pol.gate.passed ? "stamp-good" : "stamp-bad"}`}>{pol.gate.passed ? "Đạt cổng" : "Chưa đạt cổng"}</span>
              ) : (
                <span className="stamp stamp-mut">chưa đánh giá</span>
              )}
            </div>
            <h1 className="display text-[42px] leading-none mt-3 mono" style={{ fontFamily: "var(--font-plex-mono)", letterSpacing: "-0.02em" }}>
              {run.run_id}
            </h1>
            <p className="text-mut mt-2 max-w-[700px]">{PHASE_BLURB[run.phase]}</p>
            <div className="mt-2 mono text-[12px] text-dim">
              cấu hình {run.files.config} · commit {String(tm.git_commit ?? "—").slice(0, 10)} · python {String(tm.python ?? "—")}
            </div>
          </div>
          <div className="flex panel px-5 py-3">
            <div className="readout">
              <div className="v">
                {tm.timesteps_done !== undefined ? (
                  <Provenance runId={run.run_id} file={run.files.train_meta} extra="timesteps_done">
                    {fmtSteps(Number(tm.timesteps_done))}
                  </Provenance>
                ) : run.progress ? (
                  <Provenance runId={run.run_id} file={run.progress.file}>
                    <span className="text-acc2">{fmtSteps(run.progress.timesteps)}</span>
                  </Provenance>
                ) : (
                  "—"
                )}
              </div>
              <div className="l eyebrow">bước</div>
            </div>
            <div className="readout">
              <div className="v">
                {tm.wall_time_sec !== undefined ? (
                  <Provenance runId={run.run_id} file={run.files.train_meta} extra="wall_time_sec">
                    {fmtDur(Number(tm.wall_time_sec))}
                  </Provenance>
                ) : (
                  fmtDur(run.progress?.wall_time)
                )}
              </div>
              <div className="l eyebrow">thời gian</div>
            </div>
            <div className="readout">
              <div className="v">
                {tm.steps_per_sec !== undefined ? (
                  <Provenance runId={run.run_id} file={run.files.train_meta} extra="steps_per_sec">
                    {fmt(Number(tm.steps_per_sec), 0)}
                  </Provenance>
                ) : (
                  "—"
                )}
              </div>
              <div className="l eyebrow">bước/s</div>
            </div>
            <div className="readout">
              <div className="v">
                {String(tm.n_envs ?? algoCfg.n_envs ?? "—")}
              </div>
              <div className="l eyebrow">env song song</div>
            </div>
          </div>
        </div>
      </section>

      {live && (
        <section className="reveal" style={{ animationDelay: "60ms" }}>
          <LiveTraining run={run} />
        </section>
      )}

      {/* ── huấn luyện ── */}
      <section className="panel reveal" style={{ animationDelay: "120ms" }}>
        <div className="panel-head">
          <h2>Đường cong huấn luyện</h2>
          <Provenance runId={run.run_id} file={curve?.file || run.files.train_log}>
            <span className="eyebrow">train_log.csv · mỗi điểm là một rollout</span>
          </Provenance>
          <span className="flex-1" />
          {run.curriculum.length > 0 && (
            <span className="eyebrow" style={{ color: "var(--acc-2)" }}>
              curriculum: {run.curriculum.map((c) => `${c.from}→${c.to} @ ${fmtSteps(c.timesteps)}`).join(" · ")}
            </span>
          )}
        </div>
        <div className="panel-body">
          {curve ? <LearningCurve rows={curve.rows} curriculum={run.curriculum} /> : <div className="text-mut">đang đọc train_log.csv…</div>}
          <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 mono text-[11.5px] text-dim">
            {["total_steps", "n_steps", "batch_size", "n_epochs", "learning_rate", "gamma", "ent_coef"].map((k) => algoCfg[k] !== undefined && (
              <span key={k}>
                {k} <span className="text-mut">{String(algoCfg[k])}</span>
              </span>
            ))}
            {["task", "ctrl_freq", "speed_limit", "episode_sec"].map((k) => envCfg[k] !== undefined && (
              <span key={k}>
                env.{k} <span className="text-mut">{String(envCfg[k])}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── xem lại quá trình huấn luyện ── */}
      <section className="panel reveal" style={{ animationDelay: "150ms" }}>
        <div className="panel-head">
          <h2>Xem lại quá trình huấn luyện</h2>
          <span className="eyebrow">mỗi checkpoint bay thử trên seed đánh giá · tua qua từng mốc trong viewer 3D</span>
        </div>
        <div className="panel-body">
          <TrainingTimeline runId={run.run_id} phase={run.phase} />
        </div>
      </section>

      {/* ── policy so baseline ── */}
      <section className="panel reveal" style={{ animationDelay: "180ms" }}>
        <div className="panel-head">
          <h2>Policy so với baseline</h2>
          <span className="eyebrow">seed đánh giá ≥ 9000 · không chồng seed train</span>
        </div>
        <div className="panel-body pt-2">
          <MetricsTable runId={run.run_id} phase={run.phase} evals={run.evals} algo={run.algo} />
        </div>
      </section>

      {/* ── phát lại 3D ── */}
      <section className="panel reveal" style={{ animationDelay: "240ms" }}>
        <div className="panel-head flex-wrap">
          <h2>Phát lại 3D</h2>
          <span className="eyebrow">Three.js · mô hình Crazyflie 2.x thật</span>
          <span className="flex-1" />
          {run.evals.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <select
                value={tag}
                onChange={(e) => {
                  setTag(e.target.value);
                  const t = run.evals.find((x) => x.tag === e.target.value);
                  setSeed(t?.seeds[0] ?? null);
                  setOutcomeFilter("all");
                }}
              >
                {run.evals.map((e) => (
                  <option key={e.tag} value={e.tag}>
                    {e.tag} ({e.seeds.length} quỹ đạo)
                  </option>
                ))}
              </select>
              <select value={outcomeFilter} onChange={(e) => setOutcomeFilter(e.target.value as "all" | "fail" | "ok")}>
                <option value="all">mọi lượt{epStats ? ` (${epStats.n})` : ""}</option>
                <option value="ok">chỉ thành công{epStats ? ` (${epStats.ok})` : ""}</option>
                <option value="fail">chỉ thất bại{epStats ? ` (${epStats.n - epStats.ok})` : ""}</option>
              </select>
              <select value={seed ?? ""} onChange={(e) => setSeed(Number(e.target.value))}>
                {(seedRows.length ? seedRows.map((r) => r.seed) : ev?.seeds ?? []).map((s) => {
                  const r = episodes.find((x) => x.seed === s);
                  const mark = r ? (r.crashed ? `✘ ${r.reason}` : r.success ? "✔" : "⏱ hết giờ") : "";
                  return (
                    <option key={s} value={s}>
                      seed {s} {mark}
                    </option>
                  );
                })}
              </select>
            </div>
          )}
        </div>
        <div className="panel-body">
          {ev && seed !== null ? (
            <>
              <ViewerFrame runId={run.run_id} tag={tag} seed={seed} />
              <div className="mt-2 flex items-center gap-4 flex-wrap mono text-[11.5px] text-dim">
                <span>file: results/{run.run_id}/eval/{tag}/traj_{seed}.json</span>
                {epStats && (
                  <span>
                    {epStats.ok}/{epStats.n} thành công · {epStats.crash} rơi
                  </span>
                )}
                <span className="flex-1" />
                <a href={viewerUrl(run.run_id, tag, seed)} target="_blank" className="chip chip-acc">
                  mở viewer toàn màn hình ↗
                </a>
              </div>
            </>
          ) : (
            <div className="text-mut p-3 border border-dashed border-line2">Chưa có quỹ đạo để phát. Đánh giá xong sẽ có traj_&lt;seed&gt;.json.</div>
          )}
        </div>
      </section>
    </div>
  );
}

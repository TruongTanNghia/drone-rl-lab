"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";
import Provenance from "@/components/Provenance";
import { api, etaSec, fmt, fmtDur, fmtSteps, PHASE_TITLES, type CurveRow, type RunSummary } from "@/lib/api";

// Thẻ theo dõi một run đang train: thanh tiến độ, số đo mới nhất, đường return thu nhỏ.
export default function LiveTraining({ run }: { run: RunSummary }) {
  const p = run.progress;
  const [rows, setRows] = useState<CurveRow[]>([]);
  useEffect(() => {
    let alive = true;
    api<{ rows: CurveRow[] }>(`/api/runs/${run.run_id}/curve`)
      .then((c) => alive && setRows(c.rows))
      .catch(() => alive && setRows([]));
    return () => {
      alive = false;
    };
  }, [run.run_id, p?.timesteps]);

  const pct = p && p.total_steps ? Math.min(100, (100 * p.timesteps) / p.total_steps) : 0;
  const eta = etaSec(p);
  const rate = p && p.wall_time ? p.timesteps / p.wall_time : null;
  // "now" cập nhật trong effect (không gọi Date.now() khi render) để phát hiện log đứng > 5 phút
  const [now, setNow] = useState<number>(0);
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 15000); // lần đầu sau 15 s
    return () => clearInterval(id);
  }, []);
  const stale = p && now ? now / 1000 - p.log_mtime > 300 : false;

  return (
    <div className="border border-line p-4 relative overflow-hidden" style={{ background: "rgba(0,0,0,0.25)" }}>
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className={`lamp ${stale ? "lamp-warn" : "lamp-acc"}`} />
        <Link href={`/runs/${run.run_id}`} className="mono text-[15px] text-txt">
          {run.run_id}
        </Link>
        <span className="chip">
          {run.phase.toUpperCase()} · {PHASE_TITLES[run.phase]}
        </span>
        <span className="chip">
          {run.algo.toUpperCase()} · seed {run.train_seed}
        </span>
        {p?.stage && p.stage !== "default" && <span className="chip chip-cyan">stage {p.stage}</span>}
        {stale && <span className="chip chip-bad">log không đổi &gt; 5 ph</span>}
      </div>

      {p ? (
        <>
          <div className="mt-3 flex items-baseline justify-between mono text-[12px]">
            <span>
              <Provenance runId={run.run_id} file={p.file} extra="dòng cuối train_log.csv">
                <b className="text-acc2 text-[14px]">{fmtSteps(p.timesteps)}</b>
              </Provenance>
              <span className="text-mut"> / {fmtSteps(p.total_steps)} bước</span>
            </span>
            <span className="text-mut">
              {pct.toFixed(1)}% · {rate ? `${fmt(rate, 0)} bước/s` : "—"} · còn ước {fmtDur(eta)}
            </span>
          </div>
          <div className={`bar mt-1 ${stale ? "" : "live"}`}>
            <i style={{ width: `${pct}%` }} />
          </div>

          <div className="mt-3 grid gap-3 items-end" style={{ gridTemplateColumns: "auto auto auto minmax(120px, 1fr)" }}>
            <div className="readout">
              <div className="v">
                <Provenance runId={run.run_id} file={p.file} extra="ep_rew_mean">
                  {fmt(p.ep_rew_mean, 1)}
                </Provenance>
              </div>
              <div className="l eyebrow">return TB</div>
            </div>
            <div className="readout">
              <div className="v">
                <Provenance runId={run.run_id} file={p.file} extra="success_rate (100 lượt gần nhất)">
                  {p.success_rate === null ? "—" : `${(p.success_rate * 100).toFixed(0)}`}
                </Provenance>
                <small>%</small>
              </div>
              <div className="l eyebrow">thành công</div>
            </div>
            <div className="readout">
              <div className="v">
                {fmt(p.ep_len_mean, 0)}
              </div>
              <div className="l eyebrow">bước/lượt</div>
            </div>
            <div style={{ height: 56 }}>
              {rows.length > 1 && (
                <ResponsiveContainer width="100%" height={56}>
                  <AreaChart data={rows} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id={`g-${run.run_id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f2a93b" stopOpacity={0.55} />
                        <stop offset="100%" stopColor="#f2a93b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <YAxis hide domain={["auto", "auto"]} />
                    <Area type="monotone" dataKey="ep_rew_mean" stroke="#f2a93b" fill={`url(#g-${run.run_id})`} strokeWidth={1.5} dot={false} isAnimationActive={false} connectNulls />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
          <div className="mt-2 eyebrow" style={{ letterSpacing: "0.1em" }}>
            {fmtDur(p.wall_time)} đã chạy · ước tính từ tốc độ trung bình của chính run này
          </div>
        </>
      ) : (
        <div className="text-mut mt-3 text-[13px]">Chưa có dòng nào trong train_log.csv.</div>
      )}
    </div>
  );
}

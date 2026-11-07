"use client";

import Link from "next/link";
import Provenance from "@/components/Provenance";
import { fmt, fmtDur, fmtSteps, isTraining, PHASE_TITLES, type RunSummary } from "@/lib/api";

export default function RunsTable({ runs }: { runs: RunSummary[] }) {
  if (runs.length === 0)
    return (
      <div className="text-mut p-3 border border-dashed border-line2">
        results/ trống. Lệnh: <code>python train.py --config configs/g1_hover.yaml --seed 0</code>
      </div>
    );
  const sorted = [...runs].sort((a, b) => b.run_id.localeCompare(a.run_id));
  return (
    <table className="data">
      <thead>
        <tr>
          <th>run_id</th>
          <th>giai đoạn</th>
          <th>algo · seed</th>
          <th>bước</th>
          <th>thời gian</th>
          <th>bước/s</th>
          <th>đánh giá</th>
          <th>cổng</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((r) => {
          const pol = r.evals.find((e) => e.controller === r.algo && !e.source) ?? r.evals.find((e) => e.controller === r.algo);
          const live = isTraining(r);
          const tm = r.train_meta;
          return (
            <tr key={r.run_id} className={live ? "hi" : ""}>
              <td className="mono">
                {live && <span className="lamp lamp-acc mr-2" />}
                <Link href={`/runs/${r.run_id}`}>{r.run_id}</Link>
              </td>
              <td>
                <span className="chip">{r.phase.toUpperCase()}</span> <span className="text-mut text-[12.5px]">{PHASE_TITLES[r.phase]}</span>
              </td>
              <td className="mono">
                {r.algo.toUpperCase()} <span className="text-mut">· s{r.train_seed}</span>
              </td>
              <td className="mono">
                {tm ? (
                  <Provenance runId={r.run_id} file={r.files.train_meta}>
                    {fmtSteps(Number(tm.timesteps_done))}
                  </Provenance>
                ) : r.progress ? (
                  <Provenance runId={r.run_id} file={r.progress.file} extra="dòng cuối train_log.csv">
                    <span className="text-acc2">{fmtSteps(r.progress.timesteps)}</span>
                    <span className="text-mut"> / {fmtSteps(r.progress.total_steps)}</span>
                  </Provenance>
                ) : (
                  "—"
                )}
              </td>
              <td className="mono text-mut">
                {tm ? (
                  <Provenance runId={r.run_id} file={r.files.train_meta}>
                    {fmtDur(Number(tm.wall_time_sec))}
                  </Provenance>
                ) : r.progress ? (
                  fmtDur(r.progress.wall_time)
                ) : (
                  "—"
                )}
              </td>
              <td className="mono">
                {tm ? (
                  <Provenance runId={r.run_id} file={r.files.train_meta}>
                    {fmt(Number(tm.steps_per_sec), 0)}
                  </Provenance>
                ) : (
                  "—"
                )}
              </td>
              <td className="text-mut text-[12.5px] mono">{r.evals.map((e) => e.tag).join(" · ") || "chưa"}</td>
              <td>
                {live ? (
                  <span className="stamp stamp-warn">đang train</span>
                ) : r.status === "đã dừng" ? (
                  <span className="stamp stamp-mut">đã dừng</span>
                ) : pol ? (
                  <Provenance runId={r.run_id} file={pol.file} extra={`rule: ${pol.gate.rule}`}>
                    <span className={`stamp ${pol.gate.passed ? "stamp-good" : "stamp-bad"}`}>{pol.gate.passed ? "Đạt" : "Chưa đạt"}</span>
                  </Provenance>
                ) : (
                  <span className="stamp stamp-mut">chưa đánh giá</span>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

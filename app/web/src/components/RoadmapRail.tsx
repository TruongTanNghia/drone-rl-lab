"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import Provenance from "@/components/Provenance";
import { fmt, GATE_SPEC, isTraining, PHASE_BLURB, PHASE_TITLES, PHASES, type RoadmapItem, type RunSummary } from "@/lib/api";

const STATUS_LABEL: Record<RoadmapItem["status"], { cls: string; text: string }> = {
  "chưa chạy": { cls: "chip", text: "chưa chạy" },
  "chưa đánh giá": { cls: "chip chip-acc", text: "chưa đánh giá" },
  đạt: { cls: "chip chip-good", text: "đạt" },
  "chưa đạt": { cls: "chip chip-bad", text: "chưa đạt" },
};

export default function RoadmapRail({ roadmap, runs }: { roadmap: RoadmapItem[]; runs: RunSummary[] }) {
  const byPhase = useMemo(() => Object.fromEntries(roadmap.map((p) => [p.phase, p])), [roadmap]);
  const trainingPhases = useMemo(() => new Set(runs.filter(isTraining).map((r) => r.phase)), [runs]);
  // mặc định chọn giai đoạn xa nhất đã có run
  const defaultSel = useMemo(() => {
    const withRuns = PHASES.filter((p) => (byPhase[p]?.n_runs ?? 0) > 0);
    return withRuns[withRuns.length - 1] ?? "g0";
  }, [byPhase]);
  const [sel, setSel] = useState<string>(defaultSel);
  const cur = byPhase[sel];
  const curRuns = runs.filter((r) => r.phase === sel);

  return (
    <div>
      <div className="rail">
        {PHASES.map((ph, i) => {
          const p = byPhase[ph];
          const live = trainingPhases.has(ph);
          const nodeCls = live ? "s-run" : p ? `s-${p.status.replace(/ /g, "-")}` : "";
          return (
            <div key={ph} className={`station reveal ${sel === ph ? "sel" : ""}`} style={{ animationDelay: `${120 + i * 60}ms` }} onClick={() => setSel(ph)} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && setSel(ph)}>
              <div className={`node ${nodeCls}`}>{ph.toUpperCase()}</div>
              <div className="t">{PHASE_TITLES[ph]}</div>
              <div className="s">
                {live ? (
                  <span className="chip chip-acc">
                    <span className="lamp lamp-acc" /> đang train
                  </span>
                ) : p ? (
                  <span className={STATUS_LABEL[p.status].cls}>{STATUS_LABEL[p.status].text}</span>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid gap-6 border-t border-line pt-4" style={{ gridTemplateColumns: "minmax(260px, 1fr) minmax(0, 2fr)" }}>
        <div>
          <div className="eyebrow">{sel.toUpperCase()} · {PHASE_TITLES[sel]}</div>
          <p className="mt-2 text-[13.5px]">{PHASE_BLURB[sel]}</p>
          <div className="mt-3 eyebrow" style={{ letterSpacing: "0.12em" }}>Ngưỡng cổng</div>
          <div className="mono text-[12.5px] text-acc2 mt-1">{GATE_SPEC[sel]}</div>
          <div className="mt-3 text-mut text-[12.5px]">
            {cur?.n_runs ?? 0} run · {curRuns.filter(isTraining).length} đang train
          </div>
        </div>
        <div>
          {cur && cur.gates.length > 0 ? (
            <table className="data">
              <thead>
                <tr>
                  <th>run</th>
                  <th>đánh giá</th>
                  <th>giá trị</th>
                  <th>luật</th>
                  <th>kết quả</th>
                </tr>
              </thead>
              <tbody>
                {cur.gates.map((g) => (
                  <tr key={g.run_id + g.tag}>
                    <td className="mono">
                      <Link href={`/runs/${g.run_id}`}>{g.run_id}</Link>
                    </td>
                    <td className="mono text-mut">{g.tag}</td>
                    <td className="mono">
                      <Provenance runId={g.run_id} file={g.file} extra={`rule: ${g.rule}`}>
                        {fmt(g.value)}
                      </Provenance>
                    </td>
                    <td className="mono text-mut text-[12px]">{g.rule}</td>
                    <td>
                      <span className={`stamp ${g.passed ? "stamp-good" : "stamp-bad"}`}>{g.passed ? "Đạt" : "Chưa đạt"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-mut text-[13px] p-3 border border-dashed border-line2">
              {cur && cur.n_runs > 0 ? (
                <>
                  Có run nhưng chưa đánh giá policy. Lệnh:
                  <pre className="mono mt-2 text-txt text-[12px]">{`python evaluate.py --run results/<run> --controller ppo --episodes 100`}</pre>
                </>
              ) : (
                <>
                  Chưa có run nào ở {sel.toUpperCase()}. Lệnh:
                  <pre className="mono mt-2 text-txt text-[12px]">{`python train.py --config configs/${sel}_*.yaml --seed 0`}</pre>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

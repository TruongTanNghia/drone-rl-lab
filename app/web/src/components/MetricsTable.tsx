"use client";

import Provenance from "@/components/Provenance";
import { CONTROLLER_NAMES, fmt, METRIC_LABELS, PHASE_METRICS, type EvalSummary } from "@/lib/api";

export default function MetricsTable({ runId, phase, evals, algo }: { runId: string; phase: string; evals: EvalSummary[]; algo: string }) {
  if (!evals.length)
    return (
      <div className="text-mut p-3 border border-dashed border-line2">
        Chưa có đánh giá. Lệnh: <code>python evaluate.py --run results/{runId} --controller ppo --episodes 100</code>
      </div>
    );
  const keys = PHASE_METRICS[phase] ?? Object.keys(evals[0].metrics);
  const order = ["ppo", "sac", "pid", "apf", "bbox", "random"];
  const sorted = [...evals].sort((a, b) => order.indexOf(a.controller) - order.indexOf(b.controller) || String(a.source).localeCompare(String(b.source)));
  return (
    <table className="data">
      <thead>
        <tr>
          <th>controller</th>
          <th>lượt</th>
          <th>seed</th>
          {keys.map((k) => (
            <th key={k}>{METRIC_LABELS[k] ?? k}</th>
          ))}
          <th>cổng</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((e) => (
          <tr key={e.tag} className={e.controller === algo ? "hi" : ""}>
            <td>
              <span className={e.controller === algo ? "text-acc2" : ""}>{CONTROLLER_NAMES[e.controller] ?? e.controller}</span>
              {e.source && <span className="chip chip-cyan ml-2">source={e.source}</span>}
              {e.controller === algo && <span className="eyebrow ml-2" style={{ letterSpacing: "0.1em" }}>policy</span>}
            </td>
            <td className="mono">
              <Provenance runId={runId} file={e.file} extra="n_episodes">
                {e.n_episodes}
              </Provenance>
            </td>
            <td className="mono text-mut">{e.seeds.length ? `${e.seeds[0]}–${e.seeds[e.seeds.length - 1]}` : "—"}</td>
            {keys.map((k) => (
              <td key={k} className="mono">
                <Provenance runId={runId} file={e.file} extra={`metrics.${k}`}>
                  {fmt(e.metrics[k])}
                </Provenance>
              </td>
            ))}
            <td>
              <Provenance runId={runId} file={e.file} extra={`rule: ${e.gate.rule}`}>
                <span className={`stamp ${e.gate.passed ? "stamp-good" : "stamp-bad"}`}>{e.gate.passed ? "Đạt" : "Chưa đạt"}</span>
              </Provenance>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

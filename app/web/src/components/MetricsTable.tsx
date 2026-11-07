"use client";

import Provenance from "@/components/Provenance";
import { fmt, METRIC_LABELS, PHASE_METRICS, type EvalSummary } from "@/lib/api";

const NAMES: Record<string, string> = { ppo: "PPO", sac: "SAC", pid: "PIDBaseline", apf: "APFBaseline", bbox: "BBoxServoBaseline", random: "Random" };

export default function MetricsTable({ runId, phase, evals }: { runId: string; phase: string; evals: EvalSummary[] }) {
  if (!evals.length) return <div className="text-mut">Chưa có đánh giá nào. Chạy <span className="mono">python evaluate.py --run results/{runId} --controller ppo --episodes 100</span>.</div>;
  const keys = PHASE_METRICS[phase] ?? Object.keys(evals[0].metrics);
  const order = ["ppo", "sac", "pid", "apf", "bbox", "random"];
  const sorted = [...evals].sort((a, b) => (order.indexOf(a.controller) - order.indexOf(b.controller)) || String(a.source).localeCompare(String(b.source)));
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
          <tr key={e.tag}>
            <td>
              {NAMES[e.controller] ?? e.controller}
              {e.source && <span className="text-mut"> (source={e.source})</span>}
            </td>
            <td>
              <Provenance runId={runId} file={e.file}>
                {e.n_episodes}
              </Provenance>
            </td>
            <td className="mono text-mut">
              {e.seeds.length ? `${e.seeds[0]}–${e.seeds[e.seeds.length - 1]}` : "—"}
            </td>
            {keys.map((k) => (
              <td key={k} className="mono">
                <Provenance runId={runId} file={e.file} extra={`metrics.${k}`}>
                  {fmt(e.metrics[k])}
                </Provenance>
              </td>
            ))}
            <td>
              <Provenance runId={runId} file={e.file} extra={`rule: ${e.gate.rule}`}>
                <span className={`badge ${e.gate.passed ? "badge-good" : "badge-bad"}`}>{e.gate.passed ? "ĐẠT" : "CHƯA ĐẠT"}</span>
              </Provenance>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

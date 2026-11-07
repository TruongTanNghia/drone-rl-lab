"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Provenance from "@/components/Provenance";
import { api, ApiError, fmt, PHASE_TITLES, type RoadmapItem, type RunSummary } from "@/lib/api";

const STATUS_BADGE: Record<RoadmapItem["status"], string> = {
  "chưa chạy": "badge-mut",
  "chưa đánh giá": "badge-warn",
  đạt: "badge-good",
  "chưa đạt": "badge-bad",
};

export default function RoadmapPage() {
  const [roadmap, setRoadmap] = useState<RoadmapItem[] | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<RoadmapItem[]>("/api/roadmap"), api<RunSummary[]>("/api/runs")])
      .then(([r, u]) => {
        setRoadmap(r);
        setRuns(u);
      })
      .catch((e: unknown) => setErr(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
  }, []);

  if (err)
    return (
      <div className="card p-5 text-bad">
        Không gọi được API ({err}). Hãy chạy <code className="mono">uvicorn app.api.main:app --port 8000</code> ở thư mục gốc.
      </div>
    );
  if (!roadmap || !runs) return <div className="text-mut">Đang đọc results/…</div>;

  return (
    <div className="flex flex-col gap-6">
      <section>
        <h1 className="text-xl font-semibold mb-1">Lộ trình G0 → G5</h1>
        <p className="text-mut text-sm mb-4">Trạng thái cổng đọc từ <span className="mono">results/*/eval/*/metrics.json</span>. Giai đoạn chưa có run thì ghi &quot;chưa chạy&quot;.</p>
        <div className="grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))" }}>
          {roadmap.map((p) => (
            <div key={p.phase} className="card p-4 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="mono text-acc text-lg font-semibold">{p.phase.toUpperCase()}</span>
                <span className={`badge ${STATUS_BADGE[p.status]}`}>{p.status}</span>
              </div>
              <div className="text-txt">{PHASE_TITLES[p.phase]}</div>
              <div className="text-mut text-xs">{p.n_runs} run</div>
              {p.gates.length > 0 && (
                <ul className="text-xs mono flex flex-col gap-1 mt-1">
                  {p.gates.map((g) => (
                    <li key={g.run_id + g.tag} className="flex gap-2 items-baseline">
                      <span className={g.passed ? "text-good" : "text-bad"}>{g.passed ? "✔" : "✘"}</span>
                      <Link href={`/runs/${g.run_id}`} className="truncate">
                        {g.run_id}
                      </Link>
                      <Provenance runId={g.run_id} file={g.file} extra={`rule: ${g.rule}`}>
                        {fmt(g.value)}
                      </Provenance>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="card p-4">
        <h2 className="font-semibold mb-3">Tất cả các run ({runs.length})</h2>
        {runs.length === 0 ? (
          <div className="text-mut">results/ trống — chưa có run nào. Chạy <span className="mono">python train.py --config configs/g1_hover.yaml --seed 0</span>.</div>
        ) : (
          <table className="data">
            <thead>
              <tr>
                <th>run_id</th>
                <th>giai đoạn</th>
                <th>algo</th>
                <th>seed train</th>
                <th>bước</th>
                <th>bước/s</th>
                <th>đánh giá</th>
                <th>cổng</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => {
                const pol = r.evals.find((e) => e.controller === r.algo && !e.source) ?? r.evals.find((e) => e.controller === r.algo);
                return (
                  <tr key={r.run_id}>
                    <td className="mono">
                      <Link href={`/runs/${r.run_id}`}>{r.run_id}</Link>
                    </td>
                    <td>{r.phase.toUpperCase()}</td>
                    <td>{r.algo.toUpperCase()}</td>
                    <td>{r.train_seed}</td>
                    <td>
                      {r.train_meta ? (
                        <Provenance runId={r.run_id} file={r.files.train_meta}>
                          {String(r.train_meta.timesteps_done ?? "—")}
                        </Provenance>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td>
                      {r.train_meta ? (
                        <Provenance runId={r.run_id} file={r.files.train_meta}>
                          {String(r.train_meta.steps_per_sec ?? "—")}
                        </Provenance>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="text-mut">{r.evals.map((e) => e.tag).join(", ") || "chưa"}</td>
                    <td>
                      {pol ? (
                        <Provenance runId={r.run_id} file={pol.file} extra={`rule: ${pol.gate.rule}`}>
                          <span className={`badge ${pol.gate.passed ? "badge-good" : "badge-bad"}`}>{pol.gate.passed ? "ĐẠT" : "CHƯA ĐẠT"}</span>
                        </Provenance>
                      ) : (
                        <span className="badge badge-mut">chưa đánh giá</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

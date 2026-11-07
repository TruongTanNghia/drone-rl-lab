"use client";

import { useEffect, useMemo, useState } from "react";
import LiveTraining from "@/components/LiveTraining";
import RoadmapRail from "@/components/RoadmapRail";
import RunsTable from "@/components/RunsTable";
import { api, ApiError, isTraining, type RoadmapItem, type RunSummary } from "@/lib/api";

export default function HomePage() {
  const [roadmap, setRoadmap] = useState<RoadmapItem[] | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all([api<RoadmapItem[]>("/api/roadmap"), api<RunSummary[]>("/api/runs")])
      .then(([r, u]) => {
        if (!alive) return;
        setRoadmap(r);
        setRuns(u);
        setErr(null);
      })
      .catch((e: unknown) => alive && setErr(e instanceof ApiError ? `${e.status}: ${e.message}` : String(e)));
    return () => {
      alive = false;
    };
  }, [tick]);

  // Khi có run đang train thì làm mới mỗi 6 s để thấy tiến độ.
  const training = useMemo(() => (runs ?? []).filter(isTraining), [runs]);
  useEffect(() => {
    if (!training.length) return;
    const id = setInterval(() => setTick((t) => t + 1), 6000);
    return () => clearInterval(id);
  }, [training.length]);

  if (err)
    return (
      <div className="panel p-6 text-bad reveal">
        <div className="eyebrow mb-2">Không gọi được API</div>
        <div className="mb-3">{err}</div>
        <pre className="mono text-txt text-[12.5px]">uvicorn app.api.main:app --port 8000</pre>
      </div>
    );
  if (!roadmap || !runs) return <div className="text-mut mono text-[12.5px]">Đang đọc results/…</div>;

  const passed = roadmap.filter((p) => p.status === "đạt").length;
  const done = runs.filter((r) => !isTraining(r)).length;

  return (
    <div className="flex flex-col gap-7">
      {/* ── tiêu đề ── */}
      <section className="reveal grid gap-6 items-end" style={{ gridTemplateColumns: "minmax(0, 1fr) auto" }}>
        <div>
          <div className="eyebrow mb-3">Nhật ký bay thử · RL + DL · mô phỏng PyBullet</div>
          <h1 className="display text-[54px] leading-[0.95] max-w-[820px]">
            Dạy một chiếc Crazyflie <i>tự bay</i>, từ giữ độ cao đến bám người.
          </h1>
          <p className="text-mut mt-4 max-w-[640px] text-[14.5px]">
            Sáu cổng nghiệm thu, mỗi cổng có ngưỡng cố định và chỉ được qua bằng số đo thật trên seed chưa từng train. Rê chuột vào bất kỳ con số nào để xem nó đến từ file nào.
          </p>
        </div>
        <div className="flex gap-0 panel px-5 py-3">
          <div className="readout">
            <div className="v">
              {passed}
              <small>/ 6</small>
            </div>
            <div className="l eyebrow">cổng đã qua</div>
          </div>
          <div className="readout">
            <div className="v">{done}</div>
            <div className="l eyebrow">run xong</div>
          </div>
          <div className="readout">
            <div className="v" style={{ color: training.length ? "var(--acc-2)" : undefined }}>
              {training.length}
            </div>
            <div className="l eyebrow">đang train</div>
          </div>
        </div>
      </section>

      {/* ── ray lộ trình ── */}
      <section className="panel reveal" style={{ animationDelay: "90ms" }}>
        <div className="panel-head">
          <h2>Lộ trình G0 → G5</h2>
          <span className="eyebrow">trạng thái cổng đọc từ results/*/eval/*/metrics.json</span>
        </div>
        <div className="panel-body pt-2">
          <RoadmapRail roadmap={roadmap} runs={runs} />
        </div>
      </section>

      {/* ── đang huấn luyện ── */}
      {training.length > 0 && (
        <section className="panel reveal" style={{ animationDelay: "160ms" }}>
          <div className="panel-head">
            <h2>Đang huấn luyện</h2>
            <span className="chip chip-acc">
              <span className="lamp lamp-acc" /> cập nhật mỗi 6 s từ train_log.csv
            </span>
          </div>
          <div className="panel-body grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))" }}>
            {training.map((r) => (
              <LiveTraining key={r.run_id} run={r} />
            ))}
          </div>
        </section>
      )}

      {/* ── sổ run ── */}
      <section id="runs" className="panel reveal" style={{ animationDelay: "230ms" }}>
        <div className="panel-head">
          <h2>Sổ run</h2>
          <span className="eyebrow">{runs.length} run trong results/</span>
        </div>
        <div className="panel-body pt-2">
          <RunsTable runs={runs} />
        </div>
      </section>
    </div>
  );
}

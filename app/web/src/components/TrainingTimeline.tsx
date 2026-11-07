"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Provenance from "@/components/Provenance";
import { api, fmt, fmtSteps, METRIC_LABELS, PHASE_METRICS, type TimelineDoc, type TimelineEntry } from "@/lib/api";

// Xem lại quá trình huấn luyện: mỗi checkpoint đã được bay thử trên seed đánh giá (scripts/eval_checkpoints.py).
// Chọn mốc -> viewer nạp quỹ đạo của mốc đó (không tải lại iframe); bật "tự chuyển" thì hết lượt sẽ sang mốc kế.

type ViewerApi = { load: (doc: unknown) => void; play: () => void; pause: () => void; seek: (i: number) => void; playing: boolean };

const KEY_METRIC: Record<string, string> = { g0: "mean_pos_err_after_settle", g1: "mean_pos_err_after_settle", g2: "success_rate", g3: "success_rate", g4: "in_frame_frac" };

export default function TrainingTimeline({ runId, phase }: { runId: string; phase: string }) {
  const [doc, setDoc] = useState<TimelineDoc | null>(null);
  const [missing, setMissing] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [seed, setSeed] = useState<number | null>(null);
  const [auto, setAuto] = useState(true);
  const [ready, setReady] = useState(false);
  const iframe = useRef<HTMLIFrameElement>(null);
  const idxRef = useRef(0);
  const autoRef = useRef(true);
  useEffect(() => {
    idxRef.current = idx;
  }, [idx]);
  useEffect(() => {
    autoRef.current = auto;
  }, [auto]);

  useEffect(() => {
    let alive = true;
    api<TimelineDoc>(`/api/runs/${runId}/timeline`)
      .then((d) => {
        if (!alive) return;
        setDoc(d);
        setSeed(d.seeds[0] ?? null);
        setMissing(null);
      })
      .catch((e: unknown) => alive && setMissing(String((e as Error).message ?? e)));
    return () => {
      alive = false;
    };
  }, [runId]);

  const entries = useMemo(() => doc?.entries ?? [], [doc]);
  const cur: TimelineEntry | undefined = entries[idx];
  const keyMetric = KEY_METRIC[phase] ?? "mean_return";
  const keys = (PHASE_METRICS[phase] ?? []).slice(0, 4);

  const viewer = useCallback((): ViewerApi | null => {
    const w = iframe.current?.contentWindow as (Window & { __viewer?: ViewerApi }) | null | undefined;
    return w?.__viewer ?? null;
  }, []);

  // nạp quỹ đạo của mốc hiện tại vào viewer đang mở
  const loadInto = useCallback(
    async (i: number, s: number | null, play: boolean) => {
      const e = entries[i];
      const v = viewer();
      if (!e || s === null || !v) return;
      try {
        const traj = await api<unknown>(`/api/runs/${runId}/timeline/${e.timesteps}/traj/${s}`);
        v.load(traj);
        v.seek(0);
        if (play) v.play();
      } catch {
        /* thiếu file: viewer giữ nguyên */
      }
    },
    [entries, runId, viewer],
  );

  // viewer báo "ready" (lần đầu) và "end" (hết lượt)
  useEffect(() => {
    const onMsg = (ev: MessageEvent) => {
      if (ev.source !== iframe.current?.contentWindow) return;
      const m = ev.data as { type?: string; event?: string };
      if (m?.type !== "drone-viewer") return;
      if (m.event === "ready") setReady(true);
      if (m.event === "end" && autoRef.current && entries.length > 1) {
        const next = (idxRef.current + 1) % entries.length;
        setIdx(next);
      }
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, [entries.length]);

  // đổi mốc / seed -> nạp lại
  useEffect(() => {
    if (!ready) return;
    loadInto(idx, seed, true);
  }, [idx, seed, ready, loadInto]);

  if (missing)
    return (
      <div className="text-mut p-3 border border-dashed border-line2 text-[13px]">
        Chưa bay thử checkpoint. Lệnh:
        <pre className="mono mt-2 text-txt text-[12px]">{`python scripts/eval_checkpoints.py --run results/${runId} --episodes 3`}</pre>
      </div>
    );
  if (!doc || !cur) return <div className="text-mut mono text-[12.5px]">Đang đọc timeline…</div>;

  const vals = entries.map((e) => e.metrics[keyMetric] ?? null);
  const nums = vals.filter((v): v is number => v !== null);
  const lo = Math.min(...nums), hi = Math.max(...nums);
  const lowerBetter = keyMetric.includes("err") || keyMetric.includes("offset");
  const height = (v: number | null) => {
    if (v === null || hi === lo) return 50;
    const t = (v - lo) / (hi - lo);
    return 18 + 82 * (lowerBetter ? 1 - t : t);
  };
  const first = seed !== null ? cur.episodes.find((e) => e.seed === seed) : undefined;

  return (
    <div>
      {/* ── dải mốc ── */}
      <div className="flex items-end gap-1 overflow-x-auto pb-2 pt-3" style={{ minHeight: 150 }}>
        {entries.map((e, i) => {
          const v = e.metrics[keyMetric] ?? null;
          const sel = i === idx;
          const h = height(v);
          const ok = e.episodes.every((ep) => ep.success && !ep.crashed);
          const crash = e.episodes.some((ep) => ep.crashed);
          return (
            <button key={e.timesteps} onClick={() => setIdx(i)} className="flex flex-col items-center gap-1 flex-1 min-w-[40px] max-w-[80px] bg-transparent border-0 cursor-pointer p-0" title={`${fmtSteps(e.timesteps)} bước · ${METRIC_LABELS[keyMetric] ?? keyMetric} = ${fmt(v)}`}>
              <span className={`mono text-[10.5px] ${sel ? "text-acc2" : "text-dim"}`}>{fmt(v, 3)}</span>
              <span
                className="w-full"
                style={{
                  height: h,
                  background: sel ? "linear-gradient(180deg, var(--acc-2), var(--acc))" : crash ? "rgba(255,107,94,0.35)" : ok ? "rgba(123,216,143,0.35)" : "rgba(242,169,59,0.22)",
                  boxShadow: sel ? "0 0 18px rgba(242,169,59,0.5)" : undefined,
                  border: `1px solid ${sel ? "var(--acc-2)" : "var(--line-2)"}`,
                  transition: "height 0.4s cubic-bezier(.2,.7,.2,1), background 0.2s",
                }}
              />
              <span className={`mono text-[10.5px] ${sel ? "text-txt" : "text-mut"}`}>{fmtSteps(e.timesteps)}</span>
            </button>
          );
        })}
      </div>
      <div className="flex items-center gap-4 flex-wrap eyebrow" style={{ letterSpacing: "0.1em" }}>
        <span>cột = {METRIC_LABELS[keyMetric] ?? keyMetric} ({lowerBetter ? "thấp hơn tốt hơn" : "cao hơn tốt hơn"}) · xanh: cả {doc.n_episodes} lượt thành công · đỏ: có lượt rơi</span>
        <Provenance runId={runId} file={doc.file}>
          <span>timeline/summary.json</span>
        </Provenance>
      </div>

      {/* ── điều khiển + số đo của mốc ── */}
      <div className="mt-4 flex items-center gap-3 flex-wrap">
        <button className="btn" onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx === 0}>
          ⏮ mốc trước
        </button>
        <button className="btn" onClick={() => setIdx((i) => Math.min(entries.length - 1, i + 1))} disabled={idx === entries.length - 1}>
          mốc sau ⏭
        </button>
        <label className="chip" style={{ cursor: "pointer" }}>
          <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> tự chuyển mốc khi hết lượt
        </label>
        <select value={seed ?? ""} onChange={(e) => setSeed(Number(e.target.value))}>
          {doc.seeds.map((s) => {
            const ep = cur.episodes.find((x) => x.seed === s);
            const mark = ep ? (ep.crashed ? `✘ ${ep.reason}` : ep.success ? "✔" : "⏱") : "";
            return (
              <option key={s} value={s}>
                seed {s} {mark}
              </option>
            );
          })}
        </select>
        <span className="flex-1" />
        <span className="display text-[26px] leading-none">
          mốc <i>{idx + 1}</i> / {entries.length} · <span className="mono text-[20px]">{fmtSteps(cur.timesteps)}</span> bước
        </span>
      </div>

      <div className="mt-3 grid gap-4" style={{ gridTemplateColumns: "minmax(0, 1fr) 280px" }}>
        <div className="bezel">
          <iframe ref={iframe} src={`/viewer/index.html?file=${encodeURIComponent(`/api/runs/${runId}/timeline/${entries[0].timesteps}/traj/${doc.seeds[0]}`)}&frame=0`} title="timeline viewer" style={{ height: 560 }} />
        </div>
        <div className="flex flex-col gap-3">
          <div className="eyebrow">Checkpoint {cur.checkpoint}</div>
          {keys.map((k) => (
            <div key={k} className="readout" style={{ borderLeft: 0, padding: "6px 0" }}>
              <div className="v" style={{ fontSize: 22 }}>
                <Provenance runId={runId} file={cur.file} extra={`metrics.${k} (${doc.n_episodes} lượt, seed ${doc.seeds[0]}–${doc.seeds[doc.seeds.length - 1]})`}>
                  {fmt(cur.metrics[k])}
                </Provenance>
              </div>
              <div className="l eyebrow">{METRIC_LABELS[k] ?? k}</div>
            </div>
          ))}
          {first && (
            <div className="mono text-[12px] text-mut border-t border-line pt-3">
              lượt đang phát · seed {first.seed}: {first.crashed ? `rơi (${first.reason})` : first.success ? "thành công" : "hết giờ"} · {first.steps} bước · return {fmt(first.return, 1)}
            </div>
          )}
          <div className="mono text-[11px] text-dim">file: results/{runId}/timeline/{cur.timesteps}/traj_{seed}.json</div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurveRow } from "@/lib/api";

export default function LearningCurve({
  rows,
  curriculum,
}: {
  rows: CurveRow[];
  curriculum: { timesteps: number; from: string; to: string }[];
}) {
  if (!rows.length) return <div className="text-mut">train_log.csv trống.</div>;
  const data = rows.map((r) => ({ ...r, success_pct: r.success_rate === null ? null : r.success_rate * 100 }));
  return (
    <div className="grid gap-4" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))" }}>
      <div>
        <div className="text-mut text-xs mb-1">ep_rew_mean theo timesteps</div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
            <XAxis dataKey="timesteps" stroke="#9ca3af" tick={{ fontSize: 11 }} tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}k` : String(v))} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} width={56} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1f2937", fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="ep_rew_mean" name="return TB" stroke="#38bdf8" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls />
            <Line type="monotone" dataKey="ep_len_mean" name="độ dài lượt TB" stroke="#a78bfa" dot={false} strokeWidth={1} isAnimationActive={false} connectNulls yAxisId={0} />
            {curriculum.map((c) => (
              <ReferenceLine key={c.timesteps} x={c.timesteps} stroke="#fbbf24" strokeDasharray="4 2" label={{ value: c.to, fill: "#fbbf24", fontSize: 10, position: "top" }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div>
        <div className="text-mut text-xs mb-1">success_rate (100 lượt gần nhất, %)</div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
            <XAxis dataKey="timesteps" stroke="#9ca3af" tick={{ fontSize: 11 }} tickFormatter={(v) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}k` : String(v))} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} domain={[0, 100]} width={40} />
            <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1f2937", fontSize: 12 }} />
            <Line type="monotone" dataKey="success_pct" name="success %" stroke="#34d399" dot={false} strokeWidth={2} isAnimationActive={false} connectNulls />
            {curriculum.map((c) => (
              <ReferenceLine key={c.timesteps} x={c.timesteps} stroke="#fbbf24" strokeDasharray="4 2" />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

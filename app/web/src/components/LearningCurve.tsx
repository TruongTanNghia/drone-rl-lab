"use client";

import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CurveRow } from "@/lib/api";

const tickX = (v: number) => (v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(0)}k` : String(v));
const TIP = { background: "#0a0906", border: "1px solid #3d3628", borderLeft: "3px solid #f2a93b", fontSize: 12, fontFamily: "var(--font-plex-mono)" };

function Chart({ data, keyName, color, label, domain, curriculum, fmtV }: { data: Record<string, number | string | null>[]; keyName: string; color: string; label: string; domain?: [number, number]; curriculum: { timesteps: number; to: string }[]; fmtV?: (v: number) => string }) {
  const gid = `grad-${keyName}`;
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <span className="eyebrow" style={{ color }}>{label}</span>
        <span className="eyebrow" style={{ letterSpacing: "0.1em" }}>timesteps →</span>
      </div>
      <ResponsiveContainer width="100%" height={230}>
        <AreaChart data={data} margin={{ top: 10, right: 12, bottom: 4, left: 0 }}>
          <defs>
            <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.4} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#2b261d" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="timesteps" stroke="#6b6252" tick={{ fontSize: 10.5, fill: "#9c917c", fontFamily: "var(--font-plex-mono)" }} tickFormatter={tickX} tickLine={false} axisLine={{ stroke: "#3d3628" }} />
          <YAxis stroke="#6b6252" tick={{ fontSize: 10.5, fill: "#9c917c", fontFamily: "var(--font-plex-mono)" }} width={48} domain={domain ?? ["auto", "auto"]} tickLine={false} axisLine={false} tickFormatter={fmtV} />
          <Tooltip contentStyle={TIP} labelFormatter={(v) => `t = ${tickX(Number(v))}`} formatter={(v) => [typeof v === "number" ? v.toFixed(2) : String(v), label]} />
          <Area type="monotone" dataKey={keyName} stroke={color} fill={`url(#${gid})`} strokeWidth={1.8} dot={false} isAnimationActive={false} connectNulls />
          {curriculum.map((c) => (
            <ReferenceLine key={c.timesteps} x={c.timesteps} stroke="#ffd27a" strokeDasharray="4 3" label={{ value: c.to, fill: "#ffd27a", fontSize: 10, position: "insideTopRight", fontFamily: "var(--font-plex-mono)" }} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function LearningCurve({ rows, curriculum }: { rows: CurveRow[]; curriculum: { timesteps: number; from: string; to: string }[] }) {
  if (!rows.length) return <div className="text-mut">train_log.csv trống.</div>;
  const data = rows.map((r) => ({ ...r, success_pct: r.success_rate === null ? null : r.success_rate * 100 }));
  return (
    <div className="grid gap-6" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))" }}>
      <Chart data={data} keyName="ep_rew_mean" color="#f2a93b" label="return trung bình mỗi lượt" curriculum={curriculum} />
      <Chart data={data} keyName="success_pct" color="#7bd88f" label="tỷ lệ thành công, 100 lượt gần nhất (%)" domain={[0, 100]} curriculum={curriculum} fmtV={(v) => `${v}`} />
      <Chart data={data} keyName="ep_len_mean" color="#62c6ff" label="độ dài lượt trung bình (bước)" curriculum={curriculum} />
    </div>
  );
}

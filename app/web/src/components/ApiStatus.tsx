"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

// Đèn trạng thái FastAPI ở góc phải header: hỏi /api/health mỗi 10 s.
export default function ApiStatus() {
  const [st, setSt] = useState<{ ok: boolean; dir?: string; err?: string } | null>(null);
  useEffect(() => {
    let alive = true;
    const tick = () =>
      api<{ ok: boolean; results_dir: string }>("/api/health")
        .then((h) => alive && setSt({ ok: h.ok, dir: h.results_dir }))
        .catch((e: unknown) => alive && setSt({ ok: false, err: String(e) }));
    tick();
    const id = setInterval(tick, 10000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);
  if (!st) return <span className="chip"><span className="lamp" /> API…</span>;
  return (
    <span className={`chip ${st.ok ? "chip-good" : "chip-bad"}`} title={st.ok ? st.dir : st.err}>
      <span className={`lamp ${st.ok ? "lamp-good" : "lamp-bad"}`} />
      {st.ok ? "API · results/" : "API mất kết nối"}
    </span>
  );
}

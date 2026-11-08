"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { loadAttempts, recommend, type Attempt } from "@/lib/sim/grading";
import { LESSONS } from "@/lib/sim/lessons";

export default function HomePage() {
  const [attempts, setAttempts] = useState<Attempt[] | null>(null);
  useEffect(() => {
    const id = setTimeout(() => setAttempts(loadAttempts()), 0);
    return () => clearTimeout(id);
  }, []);
  const rec = useMemo(() => (attempts ? recommend(attempts, LESSONS) : null), [attempts]);
  const best = (id: string) => Math.max(0, ...(attempts ?? []).filter((a) => a.lessonId === id).map((a) => a.score));
  const tries = (id: string) => (attempts ?? []).filter((a) => a.lessonId === id).length;
  const recent = (attempts ?? []).slice(-8).reverse();

  return (
    <div className="flex flex-col gap-7 max-w-[1480px] mx-auto px-6 py-7">
      <section className="reveal grid gap-6 items-end" style={{ gridTemplateColumns: "minmax(0, 1fr) auto" }}>
        <div>
          <div className="eyebrow mb-3">Phần mềm huấn luyện phi công drone · sân tập mô phỏng</div>
          <h1 className="display text-[52px] leading-[0.95] max-w-[820px]">
            Cầm tay cầm, bay theo <i>giáo trình</i>, AI chấm từng thao tác.
          </h1>
          <p className="text-mut mt-4 max-w-[640px] text-[14.5px]">
            Sáu bài từ làm quen tới hạ cánh. Sau mỗi bài, AI phân tích chuỗi cần điều khiển và quỹ đạo bay để chấm điểm, chỉ ra lỗi tay run, gắt cần, over-control, lảo đảo và gợi ý bài kế tiếp.
          </p>
        </div>
        <div className="flex panel px-5 py-3">
          <div className="readout">
            <div className="v">{LESSONS.filter((l) => best(l.id) >= l.passScore).length}<small>/ {LESSONS.length}</small></div>
            <div className="l eyebrow">bài đã đạt</div>
          </div>
          <div className="readout">
            <div className="v">{attempts?.length ?? 0}</div>
            <div className="l eyebrow">lượt bay</div>
          </div>
        </div>
      </section>

      {rec && (
        <section className="panel reveal" style={{ animationDelay: "80ms" }}>
          <div className="panel-head">
            <h2>Gợi ý cho bạn</h2>
            <span className="eyebrow">cá nhân hoá theo lịch sử bay</span>
          </div>
          <div className="panel-body flex items-center gap-4 flex-wrap">
            <Link href={`/fly/${rec.lessonId}`} className="btn" style={{ borderColor: "var(--acc)", color: "var(--acc-2)", fontSize: 14, padding: "8px 16px" }}>
              ▶ Bay {rec.lessonId} · {LESSONS.find((l) => l.id === rec.lessonId)?.name}
            </Link>
            <span className="text-mut text-[13px]">{rec.why}</span>
          </div>
        </section>
      )}

      <section className="panel reveal" style={{ animationDelay: "140ms" }}>
        <div className="panel-head">
          <h2>Giáo trình</h2>
          <span className="eyebrow">mỗi bài có mục tiêu, thời gian giới hạn và điểm đạt</span>
        </div>
        <div className="panel-body grid gap-3" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))" }}>
          {LESSONS.map((l, i) => {
            const b = best(l.id);
            const passed = b >= l.passScore;
            return (
              <Link key={l.id} href={`/fly/${l.id}`} className="border border-line p-4 flex flex-col gap-2 text-txt hover:border-acc transition-colors reveal" style={{ background: "rgba(0,0,0,0.25)", animationDelay: `${160 + i * 50}ms` }}>
                <div className="flex items-center justify-between">
                  <span className="display text-[24px]">
                    <i>{l.id}</i> {l.name}
                  </span>
                  {attempts && (b > 0 ? <span className={`stamp ${passed ? "stamp-good" : "stamp-bad"}`}>{passed ? "Đạt" : "Chưa đạt"}</span> : <span className="stamp stamp-mut">chưa bay</span>)}
                </div>
                <div className="text-mut text-[12.5px]">{l.goal}</div>
                <div className="flex gap-3 mono text-[11.5px] text-dim mt-auto">
                  <span>≤ {l.timeLimit} s</span>
                  <span>đạt ≥ {l.passScore}</span>
                  {b > 0 && <span className="text-acc2">tốt nhất {b}</span>}
                  {tries(l.id) > 0 && <span>{tries(l.id)} lượt</span>}
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {recent.length > 0 && (
        <section className="panel reveal" style={{ animationDelay: "200ms" }}>
          <div className="panel-head">
            <h2>Lượt bay gần đây</h2>
            <span className="eyebrow">lưu trên máy này · bản lớp học sẽ lưu về máy chủ giảng viên</span>
          </div>
          <div className="panel-body pt-2">
            <table className="data">
              <thead>
                <tr>
                  <th>lúc</th>
                  <th>bài</th>
                  <th>điểm</th>
                  <th>điều khiển</th>
                  <th>chính xác</th>
                  <th>ổn định</th>
                  <th>hoàn thành</th>
                  <th>lỗi</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((a) => (
                  <tr key={a.date}>
                    <td className="mono text-mut">{new Date(a.date).toLocaleString("vi-VN")}</td>
                    <td className="mono">{a.lessonId}</td>
                    <td className="mono text-acc2">{a.score}</td>
                    <td className="mono">{a.parts.control}</td>
                    <td className="mono">{a.parts.accuracy}</td>
                    <td className="mono">{a.parts.stability}</td>
                    <td className="mono">{a.parts.completion}</td>
                    <td className="text-[12px]">{a.flags.map((f) => f.name).join(", ") || <span className="text-good">sạch</span>}{a.status === "failed" && <span className="text-bad"> · {a.reason}</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

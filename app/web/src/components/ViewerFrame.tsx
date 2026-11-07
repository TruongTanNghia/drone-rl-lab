"use client";

// Dùng lại nguyên bản viewer/index.html (Three.js) qua iframe; file quỹ đạo lấy từ API.
// Với G4 viewer tự hiện ô camera + khung mục tiêu khi quỹ đạo có trường bbox.
export default function ViewerFrame({ runId, tag, seed, autoplay = true }: { runId: string; tag: string; seed: number | null; autoplay?: boolean }) {
  if (seed === null) return <div className="text-mut p-4">Chọn seed để phát lại.</div>;
  const file = encodeURIComponent(`/api/runs/${runId}/eval/${tag}/traj/${seed}`);
  const src = `/viewer/index.html?file=${file}&frame=0${autoplay ? "&autoplay=1" : ""}`;
  return (
    <iframe
      key={src}
      src={src}
      title={`viewer ${runId} ${tag} ${seed}`}
      className="w-full rounded-xl border border-line bg-bg"
      style={{ height: 620 }}
      allow="fullscreen"
    />
  );
}

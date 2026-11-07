"use client";

// Dùng lại nguyên bản viewer/index.html (Three.js) qua iframe trong khung bezel; file quỹ đạo lấy từ API.
// Với G4 viewer tự hiện ô camera + khung mục tiêu khi quỹ đạo có trường bbox.
export function viewerUrl(runId: string, tag: string, seed: number, autoplay = true): string {
  const file = encodeURIComponent(`/api/runs/${runId}/eval/${tag}/traj/${seed}`);
  return `/viewer/index.html?file=${file}&frame=0${autoplay ? "&autoplay=1" : ""}`;
}

export default function ViewerFrame({ runId, tag, seed, autoplay = true }: { runId: string; tag: string; seed: number | null; autoplay?: boolean }) {
  if (seed === null) return <div className="text-mut p-4">Chọn seed để phát lại.</div>;
  const src = viewerUrl(runId, tag, seed, autoplay);
  return (
    <div className="bezel">
      <iframe key={src} src={src} title={`viewer ${runId} ${tag} ${seed}`} style={{ height: 640 }} allow="fullscreen" />
    </div>
  );
}

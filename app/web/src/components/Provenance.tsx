"use client";

// Bọc một con số: rê chuột vào thì hiện run_id và đường dẫn file nguồn (Cổng 5).
export default function Provenance({
  runId,
  file,
  extra,
  children,
}: {
  runId: string;
  file: string;
  extra?: string;
  children: React.ReactNode;
}) {
  return (
    <span className="prov">
      {children}
      <span className="tip">{`run_id: ${runId}\nfile:   ${file}${extra ? `\n${extra}` : ""}`}</span>
    </span>
  );
}

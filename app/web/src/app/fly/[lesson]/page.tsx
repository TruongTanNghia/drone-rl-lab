import Link from "next/link";
import FlightSim from "@/components/FlightSim";
import { lessonById } from "@/lib/sim/lessons";

export default async function FlyPage({ params }: { params: Promise<{ lesson: string }> }) {
  const { lesson } = await params;
  const l = lessonById(lesson.toUpperCase());
  if (!l)
    return (
      <div className="panel p-6 m-6">
        Không có bài <span className="mono">{lesson}</span>. <Link href="/">Về danh sách bài</Link>
      </div>
    );
  return <FlightSim lesson={l} />;
}

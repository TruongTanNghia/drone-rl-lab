"""Sinh bảng kết quả từ các metrics.json thật trong results/.

    python scripts/make_report.py                      # ghi docs/report_final.md (mọi giai đoạn)
    python scripts/make_report.py --phase g1 --inject docs/report_G1.md
        → thay nội dung giữa <!-- tables:start --> ... <!-- tables:end --> và <!-- gate:start --> ... <!-- gate:end -->

Không có số nào được gõ tay: mọi ô trong bảng là giá trị, trung bình hoặc độ lệch chuẩn của metrics.json.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.util import ROOT  # noqa: E402

COLUMNS = {
    "g0": [("mean_pos_err_after_settle", "sai số TB sau 3 s (m)"), ("truncation_count", "cắt lượt"), ("crash_count", "rơi"), ("success_rate", "tỷ lệ đạt"), ("mean_return", "return TB")],
    "g1": [("mean_pos_err_after_settle", "sai số TB sau 3 s (m)"), ("truncation_count", "cắt lượt"), ("crash_count", "rơi"), ("success_rate", "tỷ lệ đạt"), ("mean_return", "return TB")],
    "g2": [("success_rate", "tỷ lệ chạm đủ 4 điểm"), ("mean_finish_time", "thời gian xong TB (s)"), ("mean_reached", "số điểm chạm TB"), ("crash_count", "rơi"), ("mean_return", "return TB")],
    "g3": [("success_rate", "tới đích không va chạm"), ("collision_count", "va chạm"), ("mean_finish_time", "thời gian TB (s)"), ("mean_min_clearance", "khoảng hở nhỏ nhất TB (m)"), ("mean_return", "return TB")],
    "g4": [("in_frame_frac", "mục tiêu trong khung (tỷ lệ thời gian)"), ("visible_frac", "khung nhìn thấy"), ("crash_count", "rơi"), ("mean_final_offset", "lệch cuối (m)"), ("mean_return", "return TB")],
}
NAMES = {"ppo": "PPO", "sac": "SAC", "pid": "PIDBaseline", "apf": "APFBaseline", "bbox": "BBoxServoBaseline", "random": "Random"}


def load_all(results: Path) -> list[dict]:
    docs = []
    for mp in sorted(results.glob("g*_*/eval/*/metrics.json")):
        d = json.loads(mp.read_text(encoding="utf-8"))
        d["_file"] = mp.relative_to(ROOT).as_posix()
        d["_tag"] = mp.parent.name
        docs.append(d)
    return docs


def fmt(v, dec=3):
    if v is None:
        return "—"
    if isinstance(v, (int, np.integer)) or float(v).is_integer():
        return str(int(v))
    return f"{v:.{dec}f}"


def agg(vals: list, dec=3) -> str:
    vals = [v for v in vals if v is not None]
    if not vals:
        return "—"
    if len(vals) == 1:
        return fmt(vals[0], dec)
    a = np.array(vals, dtype=float)
    return f"{a.mean():.{dec}f} ± {a.std():.{dec}f}"


def latest_per_seed(docs: list[dict]) -> list[dict]:
    """Với mỗi (phase, controller, source, train_seed) chỉ giữ metrics mới nhất (run mới nhất)."""
    best: dict[tuple, dict] = {}
    for d in docs:
        key = (d["phase"], d["controller"], d.get("source"), d.get("train_seed"))
        if key not in best or d["created_at"] > best[key]["created_at"]:
            best[key] = d
    return list(best.values())


def phase_tables(docs: list[dict], phase: str) -> tuple[str, str]:
    ds = [d for d in latest_per_seed(docs) if d["phase"] == phase]
    if not ds:
        return f"_Chưa có metrics.json nào cho {phase.upper()} (chưa chạy)._", "**Cổng:** CHƯA CHẠY"
    cols = COLUMNS[phase]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for d in ds:
        groups[(d["controller"], d.get("source"))].append(d)
    head = "| Controller | run / seed train | lượt | " + " | ".join(c[1] for c in cols) + " | Cổng |\n"
    head += "|" + "---|" * (4 + len(cols)) + "\n"
    rows = []
    gate_lines = []
    order = ["ppo", "sac", "pid", "apf", "bbox", "random"]
    for (ctrl, src), items in sorted(groups.items(), key=lambda kv: (order.index(kv[0][0]) if kv[0][0] in order else 9, str(kv[0][1]))):
        items.sort(key=lambda d: (d.get("train_seed") or 0))
        name = NAMES.get(ctrl, ctrl) + (f" (source={src})" if src else "")
        if len(items) > 1:
            name += f" (TB ± ĐLC, {len(items)} seed)"
        runs = "<br>".join(f"`{d['run_id']}`" for d in items)
        n_eps = agg([d["n_episodes"] for d in items], 0)
        cells = [agg([d["metrics"].get(k) for d in items]) for k, _ in cols]
        gate_vals = [d["gate"]["passed"] for d in items]
        g = "ĐẠT" if all(gate_vals) else ("CHƯA ĐẠT" if ctrl in ("ppo", "sac") else ("đạt" if all(gate_vals) else "—"))
        rows.append(f"| {name} | {runs} | {n_eps} | " + " | ".join(cells) + f" | {g} |")
        if ctrl in ("ppo", "sac"):
            metric = items[0]["gate"]["rule"].split()[0]
            vals = [d["metrics"].get(metric) for d in items]
            worst = min(items, key=lambda d: (d["metrics"].get(metric) if d["metrics"].get(metric) is not None else -1e9))
            gate_lines.append(f"- {name}: quy tắc `{items[0]['gate']['rule']}`, giá trị từng seed = {', '.join(fmt(v) for v in vals)}, trung bình = {fmt(float(np.mean([v for v in vals if v is not None])) if any(v is not None for v in vals) else None)} → **{'ĐẠT' if all(gate_vals) else 'CHƯA ĐẠT'}**; seed kém nhất: `{worst['run_id']}` ({fmt(worst['metrics'].get(metric))}, rơi {worst['metrics'].get('crash_count')} lượt)")
            extra = items[0]["gate"].get("extra") or []
            for ex in extra:
                m = re.match(r"^(\w+)\s*(==|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)", ex)
                if m:
                    k, op, val = m.group(1), m.group(2), float(m.group(3))
                    ops = {"==": lambda a, b: a == b, "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, ">": lambda a, b: a > b}
                    oks = [d["metrics"].get(k) is not None and ops[op](d["metrics"][k], val) for d in items]
                    gate_lines.append(f"  - điều kiện phụ `{ex}`: {', '.join(fmt(d['metrics'].get(k)) for d in items)} → {'ĐẠT' if all(oks) else 'CHƯA ĐẠT'}")
                else:
                    gate_lines.append(f"  - điều kiện phụ (kiểm tay): {ex}")
    src_line = "\n\nNguồn: " + ", ".join(f"`{d['_file']}`" for d in ds)
    return head + "\n".join(rows) + src_line, "\n".join(gate_lines) if gate_lines else "**Cổng:** chưa có policy nào được đánh giá"


def inject(path: Path, tables: str, gate: str) -> None:
    txt = path.read_text(encoding="utf-8")
    for tag, body in (("tables", tables), ("gate", gate)):
        pat = re.compile(rf"<!-- {tag}:start -->.*?<!-- {tag}:end -->", re.S)
        rep = f"<!-- {tag}:start -->\n{body}\n<!-- {tag}:end -->"
        if not pat.search(txt):
            raise SystemExit(f"{path} thiếu đánh dấu <!-- {tag}:start/end -->")
        txt = pat.sub(lambda _m: rep, txt)
    path.write_text(txt, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--phase", default=None)
    ap.add_argument("--inject", default=None)
    ap.add_argument("--out", default=str(ROOT / "docs" / "report_final.md"))
    args = ap.parse_args()
    docs = load_all(Path(args.results))
    if args.phase and args.inject:
        t, g = phase_tables(docs, args.phase)
        inject(Path(args.inject), t, g)
        print(f"đã cập nhật {args.inject}")
        return
    parts = ["# Báo cáo tổng hợp (sinh tự động bởi scripts/make_report.py)\n", "Mọi số liệu đọc từ `results/*/eval/*/metrics.json`. Chưa chạy thì ghi \"chưa chạy\".\n"]
    for ph in ("g0", "g1", "g2", "g3", "g4"):
        t, g = phase_tables(docs, ph)
        parts.append(f"\n## {ph.upper()}\n\n{g}\n\n{t}\n")
    Path(args.out).write_text("\n".join(parts), encoding="utf-8")
    print(f"đã ghi {args.out}")


if __name__ == "__main__":
    main()

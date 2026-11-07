"""6. Mọi con số trong các bảng của docs/report_*.md phải tìm thấy trong một metrics.json
(hoặc là trung bình / độ lệch chuẩn / min / max của cùng một chỉ số qua các run cùng giai đoạn + controller)."""
import json
import re
from collections import defaultdict

import numpy as np
import pytest

NUM = re.compile(r"(?<![\w./\\-])-?\d+(?:\.\d+)?(?![\w/\\-])")


def _numbers_in(obj, out: set):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)) and obj is not None and np.isfinite(obj):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out)


def allowed_numbers(root) -> set[float]:
    allowed: set[float] = set()
    groups: dict[tuple, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for mp in (root / "results").glob("g*_*/eval/*/metrics.json"):
        doc = json.loads(mp.read_text(encoding="utf-8"))
        _numbers_in({k: v for k, v in doc.items() if k != "episodes"}, allowed)
        _numbers_in([{k: v for k, v in e.items() if k in ("seed", "steps", "t_end", "return", "err_after_settle", "reached", "finish_t", "d_min_episode", "in_frame_frac", "visible_frac")} for e in doc.get("episodes", [])], allowed)
        key = (doc["phase"], doc["controller"], doc.get("source"))
        for k, v in doc["metrics"].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v is not None:
                groups[key][k].append(float(v))
        allowed.add(float(len(doc.get("episodes", []))))
    for key, ms in groups.items():
        allowed.add(float(len(next(iter(ms.values()), []))))  # số run
        for k, vals in ms.items():
            a = np.array(vals)
            allowed.update({float(a.mean()), float(a.std()), float(a.min()), float(a.max()), float(a.sum())})
    for mp in (root / "results").glob("g*_*/train_meta.json"):
        _numbers_in(json.loads(mp.read_text(encoding="utf-8")), allowed)
    for p in ("docs/machine_bench.json", "docs/calibration.json"):
        if (root / p).exists():
            _numbers_in(json.loads((root / p).read_text(encoding="utf-8")), allowed)
    return allowed


def _matches(n: float, decimals: int, allowed: set[float]) -> bool:
    tol = 0.5 * 10 ** (-decimals) + 1e-9
    for v in allowed:
        if abs(v - n) <= tol:
            return True
        # cho phép tỉ lệ ghi theo %
        if abs(v * 100 - n) <= tol:
            return True
    return False


def test_report_numbers(root):
    reports = sorted(root.glob("docs/report_*.md"))
    if not reports:
        pytest.skip("chưa có báo cáo")
    allowed = allowed_numbers(root)
    bad = []
    for rp in reports:
        in_code = False
        for ln in rp.read_text(encoding="utf-8").splitlines():
            if ln.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code or not ln.lstrip().startswith("|"):
                continue
            if re.match(r"^\s*\|?\s*:?-{2,}", ln):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not cells or cells[0].lower() in ("controller", "mục", "giai đoạn", "chỉ số", "nguồn", "seed train"):
                pass
            for c in cells[1:] if cells and re.search(r"[A-Za-zÀ-ỹ]", cells[0]) else cells:
                for m in NUM.finditer(c):
                    tok = m.group(0)
                    n = float(tok)
                    dec = len(tok.split(".")[1]) if "." in tok else 0
                    if not _matches(n, dec, allowed):
                        bad.append(f"{rp.name}: '{tok}' trong '{ln.strip()[:90]}'")
    assert not bad, "Số không truy được về metrics.json:\n" + "\n".join(bad[:20])

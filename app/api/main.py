"""FastAPI chỉ đọc results/. Không có dữ liệu mẫu; thiếu file thì 404 kèm thông báo rõ.

    uvicorn app.api.main:app --reload --port 8000
Biến môi trường DRONE_RESULTS_DIR đổi thư mục kết quả (dùng cho test).
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[2]
RUN_RE = re.compile(r"^(g\d)_([a-z0-9]+)_s(\d+)_(\d{8}-\d{4})$")
PHASES = ["g0", "g1", "g2", "g3", "g4", "g5"]

app = FastAPI(title="Drone RL Lab API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def results_dir() -> Path:
    return Path(os.environ.get("DRONE_RESULTS_DIR", ROOT / "results"))


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(p)


def _run_dir(run_id: str) -> Path:
    if not RUN_RE.match(run_id):
        raise HTTPException(404, f"run_id '{run_id}' không đúng dạng <phase>_<algo>_s<seed>_<YYYYmmdd-HHMM>")
    d = results_dir() / run_id
    if not (d / "config.yaml").exists():
        raise HTTPException(404, f"không thấy run '{run_id}' ({_rel(d / 'config.yaml')} không tồn tại)")
    return d


def _read_json(p: Path, what: str) -> dict:
    if not p.exists():
        raise HTTPException(404, f"thiếu {what}: {_rel(p)}")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_summary(d: Path) -> dict:
    m = RUN_RE.match(d.name)
    cfg = yaml.safe_load((d / "config.yaml").read_text(encoding="utf-8"))
    meta = json.loads((d / "train_meta.json").read_text(encoding="utf-8")) if (d / "train_meta.json").exists() else None
    evals = []
    for mp in sorted(d.glob("eval/*/metrics.json")):
        doc = json.loads(mp.read_text(encoding="utf-8"))
        evals.append({
            "tag": mp.parent.name,
            "controller": doc.get("controller"),
            "source": doc.get("source"),
            "n_episodes": doc.get("n_episodes"),
            "metrics": doc.get("metrics"),
            "gate": doc.get("gate"),
            "created_at": doc.get("created_at"),
            "file": _rel(mp),
            "seeds": sorted(int(t.stem.split("_")[1]) for t in mp.parent.glob("traj_*.json")),
        })
    return {
        "run_id": d.name,
        "phase": m.group(1),
        "algo": m.group(2),
        "train_seed": int(m.group(3)),
        "created": m.group(4),
        "gate_rule": cfg.get("gate"),
        "has_model": (d / "model.zip").exists(),
        "has_curve": (d / "train_log.csv").exists(),
        "has_timeline": (d / "timeline" / "summary.json").exists(),
        "train_meta": meta,
        "status": "đã huấn luyện" if meta else ("đã dừng" if (d / "aborted.json").exists() else ("đang huấn luyện" if (d / "train_log.csv").exists() else "chưa có log")),
        "aborted": json.loads((d / "aborted.json").read_text(encoding="utf-8")) if (d / "aborted.json").exists() else None,
        "progress": _progress(d, cfg),
        "evals": evals,
        "files": {"config": _rel(d / "config.yaml"), "train_log": _rel(d / "train_log.csv"), "train_meta": _rel(d / "train_meta.json")},
    }


def _progress(d: Path, cfg: dict) -> dict | None:
    """Dòng cuối train_log.csv + tổng bước theo config: để dashboard theo dõi run đang chạy. Không có log thì None."""
    p = d / "train_log.csv"
    if not p.exists():
        return None
    last = None
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            last = r
    if last is None:
        return None
    num = lambda v: None if v in ("", "None", None) else float(v)  # noqa: E731
    return {
        "timesteps": int(float(last["timesteps"])),
        "total_steps": int((cfg.get("algo") or {}).get("total_steps") or 0),
        "ep_rew_mean": num(last.get("ep_rew_mean")),
        "ep_len_mean": num(last.get("ep_len_mean")),
        "success_rate": num(last.get("success_rate")),
        "wall_time": num(last.get("wall_time")),
        "stage": last.get("stage"),
        "log_mtime": p.stat().st_mtime,
        "file": _rel(p),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "results_dir": str(results_dir())}


@app.get("/api/runs")
def list_runs():
    rd = results_dir()
    if not rd.exists():
        return []
    runs = [p for p in rd.iterdir() if p.is_dir() and RUN_RE.match(p.name) and (p / "config.yaml").exists()]
    return [_run_summary(d) for d in sorted(runs, key=lambda p: p.name)]


@app.get("/api/roadmap")
def roadmap():
    """Trạng thái cổng G0–G5 đọc từ metrics.json (không có dữ liệu mẫu)."""
    runs = list_runs()
    out = []
    for ph in PHASES:
        rs = [r for r in runs if r["phase"] == ph]
        gates = []
        for r in rs:
            for e in r["evals"]:
                if e["gate"] and e["controller"] in ("ppo", "sac"):
                    gates.append({"run_id": r["run_id"], "tag": e["tag"], "passed": e["gate"]["passed"], "value": e["gate"]["value"], "rule": e["gate"]["rule"], "file": e["file"]})
        status = "chưa chạy" if not rs else ("chưa đánh giá" if not gates else ("đạt" if all(g["passed"] for g in gates) else "chưa đạt"))
        out.append({"phase": ph, "n_runs": len(rs), "status": status, "gates": gates})
    return out


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    d = _run_dir(run_id)
    s = _run_summary(d)
    s["config"] = yaml.safe_load((d / "config.yaml").read_text(encoding="utf-8"))
    s["curriculum"] = json.loads((d / "curriculum_log.json").read_text(encoding="utf-8")) if (d / "curriculum_log.json").exists() else []
    return s


@app.get("/api/runs/{run_id}/curve")
def get_curve(run_id: str):
    d = _run_dir(run_id)
    p = d / "train_log.csv"
    if not p.exists():
        raise HTTPException(404, f"thiếu train_log.csv: {_rel(p)}")
    rows = []
    with open(p, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k: (None if v in ("", "None") else (v if k == "stage" else float(v))) for k, v in r.items()})
    return {"run_id": run_id, "file": _rel(p), "rows": rows}


@app.get("/api/runs/{run_id}/eval/{controller}/metrics")
def get_metrics(run_id: str, controller: str):
    d = _run_dir(run_id)
    p = d / "eval" / controller / "metrics.json"
    doc = _read_json(p, f"metrics của controller '{controller}'")
    doc["file"] = _rel(p)
    return doc


@app.get("/api/runs/{run_id}/eval/{controller}/traj/{seed}")
def get_traj(run_id: str, controller: str, seed: int):
    d = _run_dir(run_id)
    p = d / "eval" / controller / f"traj_{seed}.json"
    if not p.exists():
        raise HTTPException(404, f"thiếu quỹ đạo seed {seed}: {_rel(p)}")
    return FileResponse(p, media_type="application/json", headers={"X-Source-File": _rel(p)})


@app.get("/api/runs/{run_id}/timeline")
def get_timeline(run_id: str):
    """Quá trình huấn luyện: mỗi checkpoint đã được bay thử (scripts/eval_checkpoints.py) -> timeline/summary.json."""
    d = _run_dir(run_id)
    p = d / "timeline" / "summary.json"
    doc = _read_json(p, "timeline (chạy python scripts/eval_checkpoints.py --run results/" + run_id + ")")
    doc["file"] = _rel(p)
    return doc


@app.get("/api/runs/{run_id}/timeline/{step}/traj/{seed}")
def get_timeline_traj(run_id: str, step: int, seed: int):
    d = _run_dir(run_id)
    p = d / "timeline" / str(step) / f"traj_{seed}.json"
    if not p.exists():
        raise HTTPException(404, f"thiếu quỹ đạo checkpoint {step} seed {seed}: {_rel(p)}")
    return FileResponse(p, media_type="application/json", headers={"X-Source-File": _rel(p)})


@app.get("/api/runs/{run_id}/eval/{controller}/frames/{seed}/{index}")
def get_camera_frame(run_id: str, controller: str, seed: int, index: int):
    """Ảnh camera đã lưu (G4, nếu evaluate.py --save-frames): eval/<tag>/frames_<seed>/<index>.png"""
    d = _run_dir(run_id)
    p = d / "eval" / controller / f"frames_{seed}" / f"{index:05d}.png"
    if not p.exists():
        raise HTTPException(404, f"không có khung hình {_rel(p)}")
    return FileResponse(p, media_type="image/png")

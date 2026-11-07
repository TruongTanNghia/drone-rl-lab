"""7. Khi results/ trống, API trả danh sách rỗng hoặc 404, không trả dữ liệu mẫu."""
import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DRONE_RESULTS_DIR", str(tmp_path / "empty_results"))
    import app.api.main as m

    importlib.reload(m)
    return TestClient(m.app)


def test_empty_results(client):
    assert client.get("/api/runs").json() == []
    rm = client.get("/api/roadmap").json()
    assert all(p["n_runs"] == 0 and p["status"] == "chưa chạy" and p["gates"] == [] for p in rm)
    assert client.get("/api/runs/g1_ppo_s0_20260101-0000").status_code == 404
    assert client.get("/api/runs/g1_ppo_s0_20260101-0000/curve").status_code == 404
    assert client.get("/api/runs/g1_ppo_s0_20260101-0000/eval/ppo/metrics").status_code == 404
    assert client.get("/api/runs/g1_ppo_s0_20260101-0000/eval/ppo/traj/9000").status_code == 404
    assert client.get("/api/runs/not-a-run").status_code == 404


def test_real_results_if_any(root, run_dirs):
    if not run_dirs:
        pytest.skip("chưa có run")
    os.environ["DRONE_RESULTS_DIR"] = str(root / "results")
    import app.api.main as m

    importlib.reload(m)
    c = TestClient(m.app)
    runs = c.get("/api/runs").json()
    assert {r["run_id"] for r in runs} == {d.name for d in run_dirs}
    r0 = next(r for r in runs if r["evals"])
    e0 = r0["evals"][0]
    doc = c.get(f"/api/runs/{r0['run_id']}/eval/{e0['tag']}/metrics").json()
    assert doc["run_id"] == r0["run_id"] and doc["file"].endswith("metrics.json")
    tj = c.get(f"/api/runs/{r0['run_id']}/eval/{e0['tag']}/traj/{e0['seeds'][0]}")
    assert tj.status_code == 200 and tj.json()["schema"] == "drone-traj/1"
    assert c.get(f"/api/runs/{r0['run_id']}/eval/{e0['tag']}/traj/1").status_code == 404

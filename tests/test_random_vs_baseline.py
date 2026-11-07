"""3. Chỉ số của RandomController phải khác hẳn baseline, để chắc bộ đo không trả hằng số."""
from agents.controllers import make_controller
from conftest import make_cfg
from envs.registry import make_env
from evaluation.metrics import compute_metrics
from evaluation.runner import run_eval


def test_random_vs_pid_hover():
    cfg = make_cfg("hover", episode_sec=6)
    env = make_env(cfg)
    try:
        seeds = list(range(9000, 9004))
        m_rand = compute_metrics("g1", run_eval(env, make_controller("random", env), seeds))
        m_pid = compute_metrics("g1", run_eval(env, make_controller("pid", env), seeds))
    finally:
        env.close()
    assert m_pid["mean_return"] > m_rand["mean_return"] + 5
    assert m_pid["crash_count"] < m_rand["crash_count"] or m_pid["mean_pos_err_after_settle"] is not None
    assert m_pid["mean_pos_err_after_settle"] is not None and m_pid["mean_pos_err_after_settle"] < 0.2


def test_random_vs_apf_obstacle():
    cfg = make_cfg("obstacle", episode_sec=12, speed_limit=1.5)
    env = make_env(cfg)
    try:
        seeds = list(range(9000, 9003))
        m_rand = compute_metrics("g3", run_eval(env, make_controller("random", env), seeds))
        m_apf = compute_metrics("g3", run_eval(env, make_controller("apf", env), seeds))
    finally:
        env.close()
    assert m_apf["mean_return"] != m_rand["mean_return"]
    assert m_apf["mean_return"] > m_rand["mean_return"]

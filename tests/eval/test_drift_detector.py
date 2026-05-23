from __future__ import annotations

from src.eval.alarm import check_thresholds, handle_drift_alarm
from src.eval.drift_detector import compute_drift_metrics, kl_divergence
from src.config.settings import EvalSettings


def test_kl_zero_for_identical_distributions() -> None:
    p = {"a": 0.5, "b": 0.5}
    assert kl_divergence(p, p) == 0.0


def test_kl_positive_when_distributions_differ() -> None:
    p = {"a": 0.9, "b": 0.1}
    q = {"a": 0.1, "b": 0.9}
    assert kl_divergence(p, q) > 0.0


def test_compute_drift_metrics_aggregates() -> None:
    metrics = compute_drift_metrics(
        baseline_keywords=["a", "a", "b"],
        current_keywords=["a", "c", "c"],
        cos_sims=[0.9, 0.8, 0.0],
        failed_flags=[False, False, True],
    )
    assert metrics.sample_size == 3
    assert metrics.failure_rate == 1 / 3
    assert abs(metrics.mean_cos_sim - 0.5666666666666666) < 1e-6
    assert metrics.kl_divergence >= 0.0


def test_alarm_detects_kl_breach() -> None:
    settings = EvalSettings(drift_kl_threshold=0.01)
    from src.eval.drift_detector import DriftMetrics

    metrics = DriftMetrics(
        kl_divergence=0.5,
        failure_rate=0.0,
        mean_cos_sim=0.9,
        sample_size=10,
    )
    breaches = check_thresholds(metrics, settings)
    assert any(b.metric == "kl_divergence" for b in breaches)


def test_handle_drift_alarm_no_slack_when_clean() -> None:
    settings = EvalSettings(drift_kl_threshold=1.0, slack_webhook_url="")
    from src.eval.drift_detector import DriftMetrics

    metrics = DriftMetrics(0.0, 0.0, 0.95, 5)
    assert handle_drift_alarm(metrics, settings) == []

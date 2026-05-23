"""Threshold breach logging and optional Slack webhook."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from src.config.settings import EvalSettings
from src.eval.drift_detector import DriftMetrics

logger = logging.getLogger(__name__)

DEFAULT_FAILURE_RATE_THRESHOLD = 0.25
DEFAULT_MIN_MEAN_COS_SIM = 0.70


@dataclass(frozen=True)
class ThresholdBreach:
    metric: str
    value: float
    threshold: float
    direction: str  # "above" | "below"


def check_thresholds(
    metrics: DriftMetrics,
    settings: EvalSettings,
    *,
    failure_rate_threshold: float = DEFAULT_FAILURE_RATE_THRESHOLD,
    min_mean_cos_sim: float = DEFAULT_MIN_MEAN_COS_SIM,
) -> list[ThresholdBreach]:
    breaches: list[ThresholdBreach] = []
    if metrics.kl_divergence > settings.drift_kl_threshold:
        breaches.append(
            ThresholdBreach(
                "kl_divergence",
                metrics.kl_divergence,
                settings.drift_kl_threshold,
                "above",
            )
        )
    if metrics.failure_rate > failure_rate_threshold:
        breaches.append(
            ThresholdBreach(
                "failure_rate",
                metrics.failure_rate,
                failure_rate_threshold,
                "above",
            )
        )
    if metrics.mean_cos_sim < min_mean_cos_sim:
        breaches.append(
            ThresholdBreach(
                "mean_cos_sim",
                metrics.mean_cos_sim,
                min_mean_cos_sim,
                "below",
            )
        )
    return breaches


def log_breaches(breaches: list[ThresholdBreach]) -> None:
    for b in breaches:
        logger.warning(
            "eval threshold breach: %s=%.4f (threshold %.4f, %s)",
            b.metric,
            b.value,
            b.threshold,
            b.direction,
        )


def notify_slack(
    *,
    webhook_url: str,
    breaches: list[ThresholdBreach],
    metrics: DriftMetrics,
    extra: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> bool:
    if not webhook_url or not breaches:
        return False

    lines = [
        f"*{b.metric}* {b.value:.4f} ({b.direction} {b.threshold:.4f})"
        for b in breaches
    ]
    payload = {
        "text": "LLM judge drift alert",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*LLM judge drift alert*\n"
                        f"KL={metrics.kl_divergence:.4f} "
                        f"fail_rate={metrics.failure_rate:.2%} "
                        f"mean_cos={metrics.mean_cos_sim:.4f} "
                        f"n={metrics.sample_size}\n"
                        + "\n".join(lines)
                    ),
                },
            }
        ],
    }
    if extra:
        payload["blocks"].append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": str(extra)},
            }
        )

    try:
        resp = httpx.post(webhook_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return True
    except httpx.HTTPError:
        logger.exception("Slack webhook notification failed")
        return False


def handle_drift_alarm(
    metrics: DriftMetrics,
    settings: EvalSettings,
    *,
    failure_rate_threshold: float = DEFAULT_FAILURE_RATE_THRESHOLD,
    min_mean_cos_sim: float = DEFAULT_MIN_MEAN_COS_SIM,
) -> list[ThresholdBreach]:
    """Log breaches and optionally notify Slack."""
    breaches = check_thresholds(
        metrics,
        settings,
        failure_rate_threshold=failure_rate_threshold,
        min_mean_cos_sim=min_mean_cos_sim,
    )
    if breaches:
        log_breaches(breaches)
        notify_slack(
            webhook_url=settings.slack_webhook_url,
            breaches=breaches,
            metrics=metrics,
        )
    return breaches


__all__ = [
    "ThresholdBreach",
    "check_thresholds",
    "log_breaches",
    "notify_slack",
    "handle_drift_alarm",
]

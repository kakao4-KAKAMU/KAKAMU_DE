"""Drift / 품질 알람."""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


def emit_alarm(event: str, payload: Mapping[str, Any], *, slack_webhook: str = "") -> None:
    body = {"event": event, **payload}
    logger.warning("ALARM %s", json.dumps(body, ensure_ascii=False))
    if slack_webhook:
        try:
            data = json.dumps({"text": f"[movie-rec] {event}: {body}"}).encode()
            req = urllib.request.Request(
                slack_webhook,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        except Exception:
            logger.exception("Slack webhook failed")


__all__ = ["emit_alarm"]

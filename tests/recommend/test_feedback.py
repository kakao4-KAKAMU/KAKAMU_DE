"""FeedbackRecorder maps action → reward → policy.update."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.chat.feedback import FeedbackRecorder


def test_feedback_records_positive_reward() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(arm_id="vec_heavy", context_key="u1", action="like")
    assert result.reward == 3.0
    policy.record_reward.assert_called_once_with(
        arm_id="vec_heavy", context_key="u1", reward=3.0
    )


def test_feedback_skip_is_negative() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(arm_id="baseline", context_key="u1", action="skip")
    assert result.reward == -1.0


def test_feedback_short_dwell_is_zero() -> None:
    policy = MagicMock()
    recorder = FeedbackRecorder(policy)
    result = recorder.record(
        arm_id="baseline", context_key="u1", action="dwell", dwell_seconds=5
    )
    assert result.reward == 0.0

from __future__ import annotations

from src.eval.drift_detector import DriftDetector


def test_drift_triggers_on_shift() -> None:
    d = DriftDetector(kl_threshold=0.01)
    d.set_baseline(["a", "a", "a", "b"])
    drifted, kl = d.check(["x", "x", "x", "y"])
    assert drifted is True
    assert kl > 0.01

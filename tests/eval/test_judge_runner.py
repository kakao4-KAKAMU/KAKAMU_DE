from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config.settings import EvalSettings
from src.eval.judge_runner import JudgeRunner, JudgeSample
from src.persistence.eval_score_store import EvalScoreStore


@pytest.fixture
def goldenset_tmp(tmp_path: Path) -> Path:
    path = tmp_path / "goldenset_sample.jsonl"
    rows = [
        {
            "id": "g001",
            "text": "A hero saves the city.",
            "expected": {
                "themes": ["action"],
                "sentiment": "positive",
                "keywords": ["hero", "city"],
            },
        },
        {
            "id": "g002",
            "text": "A quiet drama about family.",
            "expected": {
                "themes": ["drama"],
                "sentiment": "neutral",
                "keywords": ["family"],
            },
        },
    ]
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return path


def test_sample_daily_respects_size(goldenset_tmp: Path) -> None:
    runner = JudgeRunner(
        llm=MagicMock(),
        store=MagicMock(spec=EvalScoreStore),
        eval_settings=EvalSettings(daily_sample_size=1),
        goldenset_path=goldenset_tmp,
        rng=__import__("random").Random(0),
    )
    sampled = runner.sample_daily()
    assert len(sampled) == 1


def test_run_daily_mocks_llm_and_store(goldenset_tmp: Path) -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {
        "schema_valid": True,
        "schema_score": 0.9,
        "themes_score": 0.85,
        "sentiment_score": 0.8,
        "overall_score": 0.85,
        "predicted_themes": ["action"],
        "predicted_sentiment": "positive",
        "keywords": ["hero", "city"],
        "rationale": "ok",
    }
    store = MagicMock(spec=EvalScoreStore)
    store.insert_score.return_value = 42

    runner = JudgeRunner(
        llm=llm,
        store=store,
        eval_settings=EvalSettings(daily_sample_size=2),
        goldenset_path=goldenset_tmp,
        rng=__import__("random").Random(0),
    )
    results = runner.run_daily()
    assert len(results) == 2
    assert store.init_schema.called
    assert llm.chat_json.call_count == 2
    assert results[0]["id"] == 42
    assert results[0]["cos_sim"] > 0.0


def test_keyword_cos_sim() -> None:
    sim = JudgeRunner.keyword_cos_sim(["hero", "city"], ["hero", "city"])
    assert sim == pytest.approx(1.0)

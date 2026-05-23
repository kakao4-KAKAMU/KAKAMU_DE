from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.eval.judge_runner import JudgeRunner


def test_judge_one_calls_llm() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {"overall": 0.8}
    runner = JudgeRunner(llm=llm)
    out = runner.judge_one(
        source_id="m1",
        source_type="movie",
        raw_text="plot",
        ontology={"summary": "s"},
    )
    assert out["overall"] == 0.8
    llm.chat_json.assert_called_once()


def test_run_daily_sample_persists() -> None:
    llm = MagicMock()
    llm.chat_json.return_value = {"overall": 0.2}
    runner = JudgeRunner(llm=llm)
    samples = [
        {
            "source_id": "m1",
            "source_type": "movie",
            "raw_text": "t",
            "ontology": {},
            "keywords": ["a"],
        }
    ]
    with patch.object(runner, "persist_score") as mock_persist:
        runner.run_daily_sample(samples)
        mock_persist.assert_called_once()

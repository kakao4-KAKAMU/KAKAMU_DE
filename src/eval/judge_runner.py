"""Daily golden-set sampling, LLM judge via VLLMChatClient, eval_score persistence."""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from src.config.settings import EvalSettings, get_settings
from src.eval.judge_prompts import JUDGE_JSON_SCHEMA, build_judge_messages
from src.llm.vllm_client import VLLMChatClient
from src.persistence.eval_score_store import EvalScoreStore

logger = logging.getLogger(__name__)

DEFAULT_GOLDENSET = Path(__file__).resolve().parents[2] / "data" / "goldenset_sample.jsonl"


@dataclass(frozen=True)
class JudgeSample:
    sample_id: str
    text: str
    expected: dict[str, Any]


class JudgeRunner:
    """Run LLM judge on a daily sample and persist scores."""

    def __init__(
        self,
        *,
        llm: VLLMChatClient | None = None,
        store: EvalScoreStore | None = None,
        eval_settings: EvalSettings | None = None,
        goldenset_path: Path | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._llm = llm or VLLMChatClient()
        self._store = store or EvalScoreStore()
        self._eval = eval_settings or get_settings().eval_cfg
        self._goldenset_path = goldenset_path or DEFAULT_GOLDENSET
        self._rng = rng or random.Random()

    def load_goldenset(self) -> list[JudgeSample]:
        if not self._goldenset_path.is_file():
            raise FileNotFoundError(f"Goldenset not found: {self._goldenset_path}")
        samples: list[JudgeSample] = []
        with self._goldenset_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                samples.append(
                    JudgeSample(
                        sample_id=row["id"],
                        text=row["text"],
                        expected=row.get("expected", {}),
                    )
                )
        return samples

    def sample_daily(self, samples: list[JudgeSample] | None = None) -> list[JudgeSample]:
        pool = samples if samples is not None else self.load_goldenset()
        size = min(self._eval.daily_sample_size, len(pool))
        if size == len(pool):
            return list(pool)
        return self._rng.sample(pool, size)

    @staticmethod
    def keyword_cos_sim(expected: list[str], predicted: list[str]) -> float:
        """Bag-of-words cosine similarity (no embedding server required)."""
        if not expected and not predicted:
            return 1.0
        if not expected or not predicted:
            return 0.0
        e_ctr: dict[str, int] = {}
        p_ctr: dict[str, int] = {}
        for w in expected:
            e_ctr[w.strip().lower()] = e_ctr.get(w.strip().lower(), 0) + 1
        for w in predicted:
            p_ctr[w.strip().lower()] = p_ctr.get(w.strip().lower(), 0) + 1
        keys = set(e_ctr) | set(p_ctr)
        dot = sum(e_ctr.get(k, 0) * p_ctr.get(k, 0) for k in keys)
        norm_e = math.sqrt(sum(v * v for v in e_ctr.values()))
        norm_p = math.sqrt(sum(v * v for v in p_ctr.values()))
        if norm_e == 0 or norm_p == 0:
            return 0.0
        return dot / (norm_e * norm_p)

    def judge_one(self, sample: JudgeSample) -> dict[str, Any]:
        expected = sample.expected
        messages = build_judge_messages(
            source_text=sample.text,
            expected_themes=expected.get("themes"),
            expected_sentiment=expected.get("sentiment"),
        )
        return self._llm.chat_json(
            messages,
            user_id=f"judge:{sample.sample_id}",
            temperature=0.0,
            guided_json_schema=JUDGE_JSON_SCHEMA,
        )

    def run_daily(
        self,
        *,
        run_date: date | None = None,
        samples: list[JudgeSample] | None = None,
    ) -> list[dict[str, Any]]:
        """Sample, judge, store; return summary rows for drift/alarm."""
        self._store.init_schema()
        batch = self.sample_daily(samples)
        results: list[dict[str, Any]] = []

        for sample in batch:
            failed = False
            judge_output: dict[str, Any] = {}
            try:
                judge_output = self.judge_one(sample)
            except Exception:
                logger.exception("judge failed for %s", sample.sample_id)
                failed = True
                judge_output = {"schema_valid": False, "overall_score": 0.0, "keywords": []}

            exp_kw = sample.expected.get("keywords") or sample.expected.get("themes") or []
            pred_kw = judge_output.get("keywords") or judge_output.get("predicted_themes") or []
            cos_sim = self.keyword_cos_sim(
                list(exp_kw) if isinstance(exp_kw, list) else [],
                list(pred_kw) if isinstance(pred_kw, list) else [],
            )

            row_id = self._store.insert_score(
                sample_id=sample.sample_id,
                input_text=sample.text,
                judge_output=judge_output,
                expected=sample.expected,
                run_date=run_date,
                schema_score=_float_or_none(judge_output.get("schema_score")),
                themes_score=_float_or_none(judge_output.get("themes_score")),
                sentiment_score=_float_or_none(judge_output.get("sentiment_score")),
                overall_score=_float_or_none(judge_output.get("overall_score")),
                cos_sim=cos_sim,
                failed=failed,
                keywords=list(pred_kw) if isinstance(pred_kw, list) else None,
            )
            results.append(
                {
                    "id": row_id,
                    "sample_id": sample.sample_id,
                    "judge_output": judge_output,
                    "cos_sim": cos_sim,
                    "failed": failed,
                    "keywords": pred_kw,
                }
            )
        return results


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["JudgeSample", "JudgeRunner", "DEFAULT_GOLDENSET"]

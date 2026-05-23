"""Judge 실행 + eval_score 적재."""

from __future__ import annotations

import json
import logging
import random
from typing import Any, Optional, Sequence

import psycopg

from src.config.settings import EvalSettings, PostgresSettings, get_settings
from src.eval.alarm import emit_alarm
from src.eval.drift_detector import DriftDetector
from src.eval.judge_prompts import build_judge_messages
from src.llm.vllm_client import VLLMChatClient

logger = logging.getLogger(__name__)


class JudgeRunner:
    def __init__(
        self,
        llm: Optional[VLLMChatClient] = None,
        pg: Optional[PostgresSettings] = None,
        eval_cfg: Optional[EvalSettings] = None,
    ) -> None:
        app = get_settings()
        self._llm = llm or VLLMChatClient()
        self._pg = pg or app.postgres
        self._eval = eval_cfg or app.eval_cfg
        self._drift = DriftDetector(kl_threshold=self._eval.drift_kl_threshold)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self._pg.host,
            port=self._pg.port,
            dbname=self._pg.database,
            user=self._pg.user,
            password=self._pg.password,
        )

    def judge_one(
        self,
        *,
        source_id: str,
        source_type: str,
        raw_text: str,
        ontology: Mapping[str, Any],
    ) -> dict[str, Any]:
        messages = build_judge_messages(
            source_type=source_type,
            raw_text=raw_text,
            ontology_json=json.dumps(ontology, ensure_ascii=False),
        )
        return self._llm.chat_json(messages, user_id="judge")

    def persist_score(
        self,
        *,
        source_id: str,
        source_type: str,
        scores: Mapping[str, Any],
        judge_model: str,
        prompt_version: str,
    ) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO eval_score
                  (source_id, source_type, judge_model, prompt_version, scores)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    source_id,
                    source_type,
                    judge_model,
                    prompt_version,
                    json.dumps(scores),
                ),
            )
            conn.commit()

    def run_daily_sample(
        self,
        samples: Sequence[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        app = get_settings()
        n = min(self._eval.daily_sample_size, len(samples))
        picked = random.sample(list(samples), n) if len(samples) > n else list(samples)
        results: list[dict[str, Any]] = []
        keywords: list[str] = []

        for row in picked:
            scores = self.judge_one(
                source_id=row["source_id"],
                source_type=row["source_type"],
                raw_text=row["raw_text"],
                ontology=row["ontology"],
            )
            self.persist_score(
                source_id=row["source_id"],
                source_type=row["source_type"],
                scores=scores,
                judge_model=app.vllm_gen.model_name,
                prompt_version=app.ontology.prompt_version,
            )
            results.append(scores)
            keywords.extend(row.get("keywords", []))

        drifted, kl = self._drift.check(keywords)
        if drifted:
            emit_alarm(
                "keyword_drift",
                {"kl": kl, "threshold": self._eval.drift_kl_threshold},
                slack_webhook=self._eval.slack_webhook_url,
            )
        return results


__all__ = ["JudgeRunner"]

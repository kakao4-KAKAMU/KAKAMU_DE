"""PostgreSQL store for LLM judge eval_score rows."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Optional

import psycopg

from src.config.settings import PostgresSettings, get_settings

_SCHEMA_PATH = Path(__file__).with_name("eval_schema.sql")


class EvalScoreStore:
    def __init__(self, settings: Optional[PostgresSettings] = None) -> None:
        self._settings = settings or get_settings().postgres

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(
            host=self._settings.host,
            port=self._settings.port,
            dbname=self._settings.database,
            user=self._settings.user,
            password=self._settings.password,
        )

    def init_schema(self) -> None:
        ddl = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(ddl)
            conn.commit()

    def insert_score(
        self,
        *,
        sample_id: str,
        input_text: str,
        judge_output: dict[str, Any],
        expected: dict[str, Any] | None = None,
        source_type: str = "golden",
        run_date: date | None = None,
        schema_score: float | None = None,
        themes_score: float | None = None,
        sentiment_score: float | None = None,
        overall_score: float | None = None,
        cos_sim: float | None = None,
        failed: bool = False,
        keywords: list[str] | None = None,
    ) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO eval_score (
                    sample_id, run_date, source_type, input_text, expected,
                    judge_output, schema_score, themes_score, sentiment_score,
                    overall_score, cos_sim, failed, keywords
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    sample_id,
                    run_date or date.today(),
                    source_type,
                    input_text,
                    json.dumps(expected) if expected else None,
                    json.dumps(judge_output),
                    schema_score,
                    themes_score,
                    sentiment_score,
                    overall_score,
                    cos_sim,
                    failed,
                    json.dumps(keywords) if keywords else None,
                ),
            )
            (row_id,) = cur.fetchone()
            conn.commit()
            return int(row_id)

    def fetch_recent(
        self,
        *,
        run_date: date | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            if run_date:
                cur.execute(
                    """
                    SELECT sample_id, judge_output, overall_score, cos_sim,
                           failed, keywords
                    FROM eval_score
                    WHERE run_date = %s
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (run_date, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT sample_id, judge_output, overall_score, cos_sim,
                           failed, keywords
                    FROM eval_score
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cur.fetchall()
        return [
            {
                "sample_id": r[0],
                "judge_output": r[1],
                "overall_score": r[2],
                "cos_sim": r[3],
                "failed": r[4],
                "keywords": r[5],
            }
            for r in rows
        ]


__all__ = ["EvalScoreStore"]

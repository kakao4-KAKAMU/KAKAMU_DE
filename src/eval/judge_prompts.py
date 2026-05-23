"""LLM-as-Judge 프롬프트."""

from __future__ import annotations

from textwrap import dedent
from typing import Final

JUDGE_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 온톨로지 추출 결과를 평가하는 Judge 다.
    출력은 단일 JSON:
    {
      "schema_valid": 0.0~1.0,
      "themes_quality": 0.0~1.0,
      "sentiment_quality": 0.0~1.0,
      "overall": 0.0~1.0,
      "notes": "..."
    }
    코드펜스/설명 금지.
    """
).strip()


def build_judge_messages(
    *,
    source_type: str,
    raw_text: str,
    ontology_json: str,
) -> list[dict[str, str]]:
    user = dedent(
        f"""
        [source_type]
        {source_type}

        [raw_text]
        {raw_text}

        [ontology_json]
        {ontology_json}

        위 ontology 가 raw_text 를 얼마나 잘 반영했는지 JSON 으로 채점하라.
        """
    ).strip()
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


__all__ = ["JUDGE_SYSTEM_PROMPT", "build_judge_messages"]

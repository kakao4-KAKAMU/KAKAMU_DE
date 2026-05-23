"""LLM judge system prompt and JSON scoring schema (0–1)."""

from __future__ import annotations

from typing import Any

JUDGE_SYSTEM_PROMPT = """You are an ontology quality judge for a movie recommendation knowledge graph.

Score how well the SOURCE TEXT aligns with the EXPECTED ontology labels on three axes.
All scores must be floats in [0.0, 1.0].

Axes:
1. schema_score — structural fit: genres/themes/moods are plausible and internally consistent.
2. themes_score — overlap between predicted themes and expected themes (semantic match allowed).
3. sentiment_score — agreement between predicted sentiment valence and expected sentiment.

Also extract:
- predicted_themes: list of theme strings (lowercase snake_case)
- predicted_sentiment: one of very_negative, negative, neutral, positive, very_positive
- keywords: up to 10 salient lowercase keywords from the text
- schema_valid: true if the text is usable for ontology extraction

Return JSON only. No markdown."""

JUDGE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "schema_valid": {"type": "boolean"},
        "schema_score": {"type": "number", "minimum": 0, "maximum": 1},
        "themes_score": {"type": "number", "minimum": 0, "maximum": 1},
        "sentiment_score": {"type": "number", "minimum": 0, "maximum": 1},
        "overall_score": {"type": "number", "minimum": 0, "maximum": 1},
        "predicted_themes": {"type": "array", "items": {"type": "string"}},
        "predicted_sentiment": {
            "type": "string",
            "enum": [
                "very_negative",
                "negative",
                "neutral",
                "positive",
                "very_positive",
            ],
        },
        "keywords": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": [
        "schema_valid",
        "schema_score",
        "themes_score",
        "sentiment_score",
        "overall_score",
        "predicted_themes",
        "predicted_sentiment",
        "keywords",
    ],
    "additionalProperties": False,
}


def build_judge_messages(
    *,
    source_text: str,
    expected_themes: list[str] | None = None,
    expected_sentiment: str | None = None,
) -> list[dict[str, str]]:
    """Build chat messages for a single judge call."""
    themes = expected_themes or []
    sentiment = expected_sentiment or "neutral"
    user_payload = (
        f"SOURCE TEXT:\n{source_text.strip()}\n\n"
        f"EXPECTED THEMES: {themes}\n"
        f"EXPECTED SENTIMENT: {sentiment}"
    )
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_payload},
    ]


__all__ = [
    "JUDGE_SYSTEM_PROMPT",
    "JUDGE_JSON_SCHEMA",
    "build_judge_messages",
]

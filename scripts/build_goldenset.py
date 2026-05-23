"""Build data/goldenset_sample.jsonl with 30 dummy evaluation rows."""

from __future__ import annotations

import json
from pathlib import Path

THEMES = [
    ["action", "revenge"],
    ["romance", "melodrama"],
    ["horror", "supernatural"],
    ["sci_fi", "dystopia"],
    ["comedy", "buddy"],
]
SENTIMENTS = ["positive", "neutral", "negative", "very_positive", "very_negative"]
TEXTS = [
    "A retired detective returns for one last case in the rain-soaked city.",
    "Two strangers meet on a train and swap stories about lost love.",
    "Something watches from the attic while the family sleeps.",
    "Humanity's last colony ship drifts toward a dying star.",
    "Friends plan a disastrous heist at their high school reunion.",
]


def build_rows(count: int = 30) -> list[dict]:
    rows = []
    for i in range(count):
        rows.append(
            {
                "id": f"golden_{i + 1:03d}",
                "text": TEXTS[i % len(TEXTS)] + f" (sample {i + 1})",
                "expected": {
                    "themes": THEMES[i % len(THEMES)],
                    "sentiment": SENTIMENTS[i % len(SENTIMENTS)],
                    "keywords": ["movie", "plot", f"tag_{i % 5}"],
                },
            }
        )
    return rows


def main() -> Path:
    root = Path(__file__).resolve().parents[1]
    out = root / "data" / "goldenset_sample.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows(30)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {out}")
    return out


if __name__ == "__main__":
    main()

"""골든셋 샘플 JSONL 생성 (초기 30건)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "goldenset_sample.jsonl"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(30):
        rows.append(
            {
                "source_id": f"movie-{i:03d}",
                "source_type": "movie",
                "raw_text": f"영화 줄거리 샘플 {i}",
                "ontology": {
                    "summary": f"요약 {i}",
                    "themes": ["성장"],
                    "sentiment": "neutral",
                },
                "keywords": ["성장", "가족"],
            }
        )
    with OUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()

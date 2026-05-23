from __future__ import annotations

from unittest.mock import MagicMock

from src.config.settings import VocabSettings
from src.vocab.candidate_store import CandidateStore
from src.vocab.promoter import VocabPromoter


def test_promoter_skips_high_similarity() -> None:
    neo4j = MagicMock()
    store = MagicMock(spec=CandidateStore)
    store.list_promotion_candidates.return_value = [
        {
            "normalized": "revenge",
            "kind": "theme",
            "term": "revenge",
            "embedding": [1.0, 0.0],
        }
    ]
    promoter = VocabPromoter(
        neo4j,
        store,
        settings=VocabSettings(promote_min_count=1, promote_min_days=0, promote_max_cos_sim=0.85),
    )
    stats = promoter.run_batch([("revenge", [1.0, 0.0])])
    assert stats["aliased"] == 1

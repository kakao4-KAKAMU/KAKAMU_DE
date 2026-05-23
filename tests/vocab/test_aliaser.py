from __future__ import annotations

from src.vocab.aliaser import TermAliaser, cosine_similarity


def test_cosine_identical() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_find_alias() -> None:
    aliaser = TermAliaser(alias_threshold=0.99)
    emb = [1.0, 0.0]
    found = aliaser.find_alias(emb, [("revenge", [1.0, 0.0]), ("love", [0.0, 1.0])])
    assert found == "revenge"

"""VocabularyNormalizer library 파싱 테스트."""

from __future__ import annotations

from pathlib import Path

from src.vocab.normalizer import VocabularyNormalizer

ROOT = Path(__file__).resolve().parents[2]
LIBRARY = ROOT / "docs" / "genre_theme_mood_library.md"


def test_from_library_md_loads_korean_genre_list() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    genres = set(norm.genres())
    assert "드라마" in genres
    assert "스릴러" in genres
    assert "액션" in genres
    assert "SF" in genres
    assert "멜로/로맨스" in genres
    assert len(genres) >= 60


def test_from_library_md_loads_themes_and_moods() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    themes = set(norm.themes())
    moods = set(norm.moods())
    assert "identity" in themes
    assert "loss" in themes
    assert "melancholic" in moods
    assert "warm" in moods


def test_normalize_genre_korean_and_english_alias() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    assert norm.normalize_genre("드라마") == "드라마"
    assert norm.normalize_genre("drama") == "드라마"
    assert norm.normalize_genre("로맨스") == "멜로/로맨스"
    assert norm.normalize_genre("action") == "액션"


def test_genre_theme_mood_relations() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    assert "revenge" in norm.themes_for_genre("액션")
    assert "intense" in norm.moods_for_genre("액션")
    assert "스릴러" in norm.related_genres("액션")
    assert "justice" in norm.themes_for_genre("무협")
    assert "드라마" in norm.related_genres("가족")


def test_all_core_genres_have_ontology_relations() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    rel = norm.relations
    assert len(rel.genre_themes) == 61
    assert len(rel.genre_moods) == 61
    assert len(rel.genre_related) == 61


def test_theme_relations() -> None:
    norm = VocabularyNormalizer.from_library_md(LIBRARY)
    assert "grief" in norm.related_themes("loss")
    assert "melancholic" in norm.moods_for_theme("loss")

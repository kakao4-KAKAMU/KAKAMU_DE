"""채팅 질의 분석 온톨로지 기반 movie/feed 필터 Cypher.

``analyze_query`` 가 추출한 movie/feed 필터를 하이브리드 검색 전·후에 적용한다.
기존 ``HYBRID_*_RECOMMEND_WEIGHTED`` 를 확장해 온톨로지 관계 필터를 추가한다.
"""

from __future__ import annotations

from typing import Final

from src.graph.cypher_statements.properties import BASE_PLOT_EMBEDDING, BASE_SUMMARY_EMBEDDING

_CHAT_MOVIE_ONTOLOGY_FILTER: Final[str] = """
// 온톨로지 기본 필터 (빈 값이면 조건 무시)
  AND coalesce(m.toxicity_score, 0.0) <= $max_toxicity
  AND ($min_year = 0 OR coalesce(m.producing_year, 0) >= $min_year)
  AND ($max_year = 0 OR coalesce(m.producing_year, 9999) <= $max_year)
  AND (
    $filter_country = ''
    OR m.country = $filter_country
    OR EXISTS {
      MATCH (m)-[:PRODUCED_IN]->(c:Country)
      WHERE c.code = $filter_country OR c.name = $filter_country
    }
  )
  AND (
    size($query_genres) = 0
    OR EXISTS {
      MATCH (m)-[:HAS_GENRE]->(g:Genre)
      WHERE g.name IN $query_genres
    }
  )
  AND (
    size($query_person_names) = 0
    OR EXISTS {
      MATCH (m)-[hp:HAS_PERSON]->(p:Person)
      WHERE (hp.job STARTS WITH '출연' OR hp.job STARTS WITH '감독')
        AND (p.name IN $query_person_names or p.eng_name IN $query_person_names)
        AND p.kmdb_person_id IS NOT NULL
    }
  )
"""
# AND (
#   size($query_person_jobs) = 0
#   OR EXISTS {
#     MATCH (m)-[hp:HAS_PERSON]->(:Person)
#     WHERE hp.job IN $query_person_jobs
#   }
# )

_CHAT_FEED_ONTOLOGY_FILTER: Final[str] = """
// 온톨로지 기본 필터 (빈 값이면 조건 무시)
WITH f, vec_score
WHERE coalesce(f.toxicity_score, 0.0) <= $max_toxicity
  AND ($include_spoiler = true OR f.contains_spoiler = false)
  AND ($filter_sentiment = '' OR f.sentiment = $filter_sentiment)
  AND (
    $related_movie_title = ''
    OR EXISTS {
      MATCH (f)-[:ABOUT_MOVIE]->(rm:Movie)
      WHERE toLower(rm.title) CONTAINS toLower($related_movie_title)
    }
  )
  AND (
    size($query_categories) = 0
    OR EXISTS {
      MATCH (f)-[:HAS_CATEGORY]->(c:Category)
      WHERE c.name IN $query_categories
    }
  )
  AND (
    size($query_emotions) = 0
    OR EXISTS {
      MATCH (f)-[:HAS_EMOTION]->(em:Emotion)
      WHERE em.tag IN $query_emotions
    }
  )
"""

CHAT_MOVIE_FILTER: Final[str] = f"""
// 0) 온톨로지 필터 우선 적용
MATCH (m:Movie)
WHERE m.{BASE_PLOT_EMBEDDING} IS NOT NULL
{_CHAT_MOVIE_ONTOLOGY_FILTER}

// 1) 후보군을 넉넉하게 확보 (vec_top_k * 버퍼 배수)
WITH m, vector.similarity.cosine(m.{BASE_PLOT_EMBEDDING}, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT toInteger($vec_top_k * 5)

// Keyword / Theme / Mood 부스트
OPTIONAL MATCH (m)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH m, vec_score, count(DISTINCT k) AS kw_hits

OPTIONAL MATCH (m)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH m, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

OPTIONAL MATCH (m)-[:HAS_MOOD]->(md:Mood)
WHERE md.name IN $query_moods
WITH m, vec_score, kw_hits, theme_hits, count(DISTINCT md) AS mood_hits

// Persona / User preference 가중치
WITH m, vec_score, kw_hits, theme_hits, mood_hits,
     ($persona_id IS NOT NULL) AS use_persona

OPTIONAL MATCH (pe:Persona {{persona_id: $persona_id}})-[pref:PREFERS]->(x)
WHERE use_persona AND (x:Genre OR x:Theme OR x:Keyword)
OPTIONAL MATCH (m)-[:HAS_GENRE|HAS_THEME|MENTIONS]->(x)
WITH m, vec_score, kw_hits, theme_hits, mood_hits, use_persona,
     CASE WHEN use_persona THEN coalesce(sum(pref.weight), 0.0) ELSE 0.0 END AS persona_pref_score

OPTIONAL MATCH (u:User {{user_id: $user_id}})-[p:PREFERS]->(x2)
WHERE NOT use_persona AND $user_id IS NOT NULL AND (x2:Genre OR x2:Theme OR x2:Keyword)
OPTIONAL MATCH (m)-[:HAS_GENRE|HAS_THEME|MENTIONS]->(x2)
WITH m, vec_score, kw_hits, theme_hits, mood_hits, use_persona, persona_pref_score,
     CASE WHEN NOT use_persona THEN coalesce(sum(p.weight), 0.0) ELSE 0.0 END AS user_pref_score
WITH m, vec_score, kw_hits, theme_hits, mood_hits,
     persona_pref_score + user_pref_score AS pref_score

WITH m,
     ($w_vec   * vec_score)
   + ($w_kw    * (1.0 - exp(-toFloat(kw_hits))))
   + ($w_theme * (1.0 - exp(-toFloat(theme_hits))))
   + ($w_mood  * (1.0 - exp(-toFloat(mood_hits))))
   + ($w_user  * tanh(pref_score)) AS score
ORDER BY score DESC
LIMIT $top_k

RETURN m.movie_id     AS movie_id,
       m.producing_year AS producing_year,
       m.country AS country,
       m.title        AS title,
       m.plot_summary AS plot_summary,
       score
"""

CHAT_FEED_FILTER: Final[str] = f"""
// 1) summary_embedding 기반 후보군 확보
MATCH (f:Feed)
WHERE f.{BASE_SUMMARY_EMBEDDING} IS NOT NULL
  AND coalesce(f.deleted, false) = false
WITH f, vector.similarity.cosine(f.{BASE_SUMMARY_EMBEDDING}, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT toInteger($vec_top_k * 5)

{_CHAT_FEED_ONTOLOGY_FILTER}

// Keyword 부스트
OPTIONAL MATCH (f)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH f, vec_score, count(DISTINCT k) AS kw_hits

// Theme 부스트 (피드가 연결된 영화의 테마)
OPTIONAL MATCH (f)-[:ABOUT_MOVIE]->(:Movie)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH f, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

// Emotion 부스트
OPTIONAL MATCH (f)-[:HAS_EMOTION]->(em:Emotion)
WHERE em.tag IN $query_moods
WITH f, vec_score, kw_hits, theme_hits, count(DISTINCT em) AS mood_hits

// Persona / User preference 가중치
WITH f, vec_score, kw_hits, theme_hits, mood_hits,
     ($persona_id IS NOT NULL) AS use_persona

OPTIONAL MATCH (pe:Persona {{persona_id: $persona_id}})-[pref:PREFERS]->(x)
WHERE use_persona AND (x:Genre OR x:Theme OR x:Keyword OR x:Category)
OPTIONAL MATCH (f)-[:MENTIONS|HAS_CATEGORY]->(x)
WITH f, vec_score, kw_hits, theme_hits, mood_hits, use_persona,
     CASE WHEN use_persona THEN coalesce(sum(pref.weight), 0.0) ELSE 0.0 END AS persona_pref_score

OPTIONAL MATCH (u:User {{user_id: $user_id}})-[p:PREFERS]->(x2)
WHERE NOT use_persona AND $user_id IS NOT NULL AND (x2:Genre OR x2:Theme OR x2:Keyword OR x2:Category)
OPTIONAL MATCH (f)-[:MENTIONS|HAS_CATEGORY]->(x2)
WITH f, vec_score, kw_hits, theme_hits, mood_hits, use_persona, persona_pref_score,
     CASE WHEN NOT use_persona THEN coalesce(sum(p.weight), 0.0) ELSE 0.0 END AS user_pref_score
WITH f, vec_score, kw_hits, theme_hits, mood_hits,
     persona_pref_score + user_pref_score AS pref_score

WITH f,
     ($w_vec   * vec_score)
   + ($w_kw    * (1.0 - exp(-toFloat(kw_hits))))
   + ($w_theme * (1.0 - exp(-toFloat(theme_hits))))
   + ($w_mood  * (1.0 - exp(-toFloat(mood_hits))))
   + ($w_user  * tanh(pref_score)) AS score
ORDER BY score DESC
LIMIT $top_k

RETURN f.feed_id         AS feed_id,
       f.summary         AS summary,
       f.sentiment_score AS sentiment_score,
       score
"""


def build_chat_movie_filter(embedding_property: str = BASE_PLOT_EMBEDDING) -> str:
    return CHAT_MOVIE_FILTER.replace(
        f"m.{BASE_PLOT_EMBEDDING}",
        f"m.{embedding_property}",
    )


def build_chat_feed_filter(embedding_property: str = BASE_SUMMARY_EMBEDDING) -> str:
    return CHAT_FEED_FILTER.replace(
        f"f.{BASE_SUMMARY_EMBEDDING}",
        f"f.{embedding_property}",
    )


__all__ = [
    "CHAT_FEED_FILTER",
    "CHAT_MOVIE_FILTER",
    "build_chat_feed_filter",
    "build_chat_movie_filter",
]

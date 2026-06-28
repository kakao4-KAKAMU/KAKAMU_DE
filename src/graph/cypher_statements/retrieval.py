"""Hybrid retrieval Cypher (semantic + keyword)."""

from __future__ import annotations

from typing import Final

from src.graph.cypher_statements.properties import BASE_PLOT_EMBEDDING, BASE_SUMMARY_EMBEDDING

HYBRID_MOVIE_RECOMMEND_WEIGHTED: Final[str] = f"""
// 1) 후보군을 넉넉하게 확보 (vec_top_k * 버퍼 배수)
MATCH (m:Movie)
WHERE m.{BASE_PLOT_EMBEDDING} IS NOT NULL
WITH m, vector.similarity.cosine(m.{BASE_PLOT_EMBEDDING}, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT toInteger($vec_top_k * 5)   // 필터 손실 보정용 버퍼

// 2) toxicity 필터 (기존과 동일한 위치)
WITH m, vec_score
WHERE coalesce(m.toxicity_score, 0.0) <= $max_toxicity

// 3) Keyword / Theme / Mood 부스트
OPTIONAL MATCH (m)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH m, vec_score, count(DISTINCT k) AS kw_hits

OPTIONAL MATCH (m)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH m, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

OPTIONAL MATCH (m)-[:HAS_MOOD]->(md:Mood)
WHERE md.name IN $query_moods
WITH m, vec_score, kw_hits, theme_hits, count(DISTINCT md) AS mood_hits

// 4) Persona / User preference 가중치 (persona_id 있으면 Persona, 없으면 User; 노드 없으면 0)
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

// 5) 최종 스코어 산출
WITH m,
     ($w_vec   * vec_score)
   + ($w_kw    * (1.0 - exp(-toFloat(kw_hits))))
   + ($w_theme * (1.0 - exp(-toFloat(theme_hits))))
   + ($w_mood  * (1.0 - exp(-toFloat(mood_hits))))
   + ($w_user  * tanh(pref_score)) AS score
ORDER BY score DESC
LIMIT $top_k

RETURN m.movie_id     AS movie_id,
       m.title        AS title,
       m.plot_summary AS plot_summary,
       score
"""

HYBRID_FEED_RECOMMEND_WEIGHTED: Final[str] = f"""
// 1) summary_embedding 기반 후보군 확보 (vec_top_k * 버퍼 배수)
MATCH (f:Feed)
WHERE f.{BASE_SUMMARY_EMBEDDING} IS NOT NULL
  AND coalesce(f.deleted, false) = false
WITH f, vector.similarity.cosine(f.{BASE_SUMMARY_EMBEDDING}, $query_embedding) AS vec_score
ORDER BY vec_score DESC
LIMIT toInteger($vec_top_k * 5)   // 필터 손실 보정용 버퍼

// 2) toxicity / spoiler 필터
WITH f, vec_score
WHERE coalesce(f.toxicity_score, 0.0) <= $max_toxicity

// 3) Keyword 부스트
OPTIONAL MATCH (f)-[:MENTIONS]->(k:Keyword)
WHERE k.normalized IN $query_keywords
WITH f, vec_score, count(DISTINCT k) AS kw_hits

// 4) Theme 부스트 (피드가 연결된 영화의 테마)
OPTIONAL MATCH (f)-[:ABOUT_MOVIE]->(:Movie)-[:HAS_THEME]->(t:Theme)
WHERE t.name IN $query_themes
WITH f, vec_score, kw_hits, count(DISTINCT t) AS theme_hits

// 5) Mood/Emotion 부스트
OPTIONAL MATCH (f)-[:HAS_EMOTION]->(em:Emotion)
WHERE em.tag IN $query_moods
WITH f, vec_score, kw_hits, theme_hits, count(DISTINCT em) AS mood_hits

// 6) Persona / User preference 가중치 (persona_id 있으면 Persona, 없으면 User; 노드 없으면 0)
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

// 7) 최종 스코어 산출
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

__all__ = [
    "HYBRID_FEED_RECOMMEND_WEIGHTED",
    "HYBRID_MOVIE_RECOMMEND_WEIGHTED",
]

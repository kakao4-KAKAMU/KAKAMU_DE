# Movie Genre & Theme Ontology Dataset

## 목적

영화 추천 시스템, Neo4j Knowledge Graph, Semantic Retrieval, LLM Ontology Mapping에 활용 가능한 엔터프라이즈급 Genre/Theme 데이터셋.

구성 목표:

* 장르 정규화
* Theme ontology 구성
* 상위/하위 관계 정의
* Mood 연결
* Narrative Device 연결
* 추천 similarity 계산 가능 구조

---

# Genre Ontology

## Genre Schema

```json
{
  "id": "genre_action",
  "name": "action",
  "display_name_ko": "액션",
  "parent": null,
  "description": "Physical conflict, combat, pursuit, and high-energy storytelling.",
  "related_genres": [
    "thriller",
    "crime",
    "adventure"
  ],
  "common_themes": [
    "revenge",
    "survival",
    "justice"
  ],
  "common_moods": [
    "intense",
    "adrenaline",
    "suspenseful"
  ]
}
```

---

# Core Genre Dataset

## Action

```json
{
  "id": "genre_action",
  "name": "action",
  "display_name_ko": "액션",
  "related_genres": [
    "thriller",
    "adventure",
    "crime"
  ],
  "common_themes": [
    "revenge",
    "survival",
    "justice",
    "heroism"
  ],
  "common_moods": [
    "intense",
    "adrenaline",
    "violent"
  ]
}
```

---

## Drama

```json
{
  "id": "genre_drama",
  "name": "drama",
  "display_name_ko": "드라마",
  "related_genres": [
    "romance",
    "family",
    "independent"
  ],
  "common_themes": [
    "identity",
    "family",
    "loss",
    "personal_growth"
  ],
  "common_moods": [
    "emotional",
    "melancholic",
    "warm"
  ]
}
```

---

## Thriller

```json
{
  "id": "genre_thriller",
  "name": "thriller",
  "display_name_ko": "스릴러",
  "related_genres": [
    "crime",
    "mystery",
    "horror"
  ],
  "common_themes": [
    "paranoia",
    "truth",
    "survival",
    "conspiracy"
  ],
  "common_moods": [
    "tense",
    "dark",
    "suspenseful"
  ]
}
```

---

## Science Fiction

```json
{
  "id": "genre_scifi",
  "name": "science_fiction",
  "display_name_ko": "SF",
  "related_genres": [
    "cyberpunk",
    "fantasy",
    "thriller"
  ],
  "common_themes": [
    "humanity",
    "technology",
    "identity",
    "artificial_intelligence",
    "time"
  ],
  "common_moods": [
    "futuristic",
    "philosophical",
    "surreal"
  ]
}
```

---

## Horror

```json
{
  "id": "genre_horror",
  "name": "horror",
  "display_name_ko": "공포",
  "related_genres": [
    "thriller",
    "psychological",
    "supernatural"
  ],
  "common_themes": [
    "fear",
    "death",
    "madness",
    "isolation"
  ],
  "common_moods": [
    "disturbing",
    "anxious",
    "claustrophobic"
  ]
}
```

---

## Romance

```json
{
  "id": "genre_romance",
  "name": "romance",
  "display_name_ko": "로맨스",
  "related_genres": [
    "drama",
    "comedy",
    "slice_of_life"
  ],
  "common_themes": [
    "love",
    "separation",
    "emotional_connection",
    "sacrifice"
  ],
  "common_moods": [
    "warm",
    "hopeful",
    "bittersweet"
  ]
}
```

---

## Mystery

```json
{
  "id": "genre_mystery",
  "name": "mystery",
  "display_name_ko": "미스터리",
  "related_genres": [
    "thriller",
    "crime",
    "psychological"
  ],
  "common_themes": [
    "truth",
    "hidden_past",
    "obsession",
    "uncertainty"
  ],
  "common_moods": [
    "enigmatic",
    "tense",
    "suspenseful"
  ]
}
```

---

## Crime

```json
{
  "id": "genre_crime",
  "name": "crime",
  "display_name_ko": "범죄",
  "related_genres": [
    "thriller",
    "action",
    "mystery"
  ],
  "common_themes": [
    "corruption",
    "power",
    "morality",
    "betrayal"
  ],
  "common_moods": [
    "gritty",
    "dark",
    "violent"
  ]
}
```

---

## Fantasy

```json
{
  "id": "genre_fantasy",
  "name": "fantasy",
  "display_name_ko": "판타지",
  "related_genres": [
    "adventure",
    "scifi",
    "family"
  ],
  "common_themes": [
    "destiny",
    "hero_journey",
    "magic",
    "good_vs_evil"
  ],
  "common_moods": [
    "epic",
    "wonder",
    "mythical"
  ]
}
```

---

## Comedy

```json
{
  "id": "genre_comedy",
  "name": "comedy",
  "display_name_ko": "코미디",
  "related_genres": [
    "romance",
    "slice_of_life",
    "family"
  ],
  "common_themes": [
    "friendship",
    "daily_life",
    "social_satire",
    "misunderstanding"
  ],
  "common_moods": [
    "lighthearted",
    "funny",
    "chaotic"
  ]
}
```

---

# Theme Ontology

## Theme Schema

```json
{
  "id": "theme_loss",
  "name": "loss",
  "display_name_ko": "상실",
  "parent": null,
  "related_themes": [
    "grief",
    "loneliness"
  ],
  "related_moods": [
    "melancholic",
    "tragic"
  ],
  "intensity": 0.8
}
```

---

# Core Theme Dataset

## Identity

```json
{
  "id": "theme_identity",
  "name": "identity",
  "display_name_ko": "정체성",
  "parent": null,
  "children": [
    "fragmented_identity",
    "self_discovery",
    "dual_identity"
  ],
  "related_themes": [
    "existentialism",
    "memory",
    "alienation"
  ],
  "related_moods": [
    "philosophical",
    "introspective"
  ]
}
```

---

## Loss

```json
{
  "id": "theme_loss",
  "name": "loss",
  "display_name_ko": "상실",
  "children": [
    "family_loss",
    "romantic_loss",
    "self_loss"
  ],
  "related_themes": [
    "grief",
    "loneliness",
    "recovery"
  ],
  "related_moods": [
    "melancholic",
    "tragic",
    "quiet"
  ]
}
```

---

## Revenge

```json
{
  "id": "theme_revenge",
  "name": "revenge",
  "display_name_ko": "복수",
  "children": [
    "personal_revenge",
    "social_revenge"
  ],
  "related_themes": [
    "justice",
    "anger",
    "obsession"
  ],
  "related_moods": [
    "intense",
    "violent",
    "dark"
  ]
}
```

---

## Existentialism

```json
{
  "id": "theme_existentialism",
  "name": "existentialism",
  "display_name_ko": "실존주의",
  "children": [
    "meaninglessness",
    "existential_loneliness",
    "absurdity"
  ],
  "related_themes": [
    "identity",
    "alienation",
    "death"
  ],
  "related_moods": [
    "philosophical",
    "melancholic",
    "surreal"
  ]
}
```

---

## Family

```json
{
  "id": "theme_family",
  "name": "family",
  "display_name_ko": "가족",
  "children": [
    "broken_family",
    "family_conflict",
    "found_family"
  ],
  "related_themes": [
    "love",
    "sacrifice",
    "responsibility"
  ],
  "related_moods": [
    "warm",
    "emotional",
    "bittersweet"
  ]
}
```

---

## Memory

```json
{
  "id": "theme_memory",
  "name": "memory",
  "display_name_ko": "기억",
  "children": [
    "memory_loss",
    "false_memory",
    "nostalgia"
  ],
  "related_themes": [
    "identity",
    "truth",
    "time"
  ],
  "related_moods": [
    "nostalgic",
    "mysterious",
    "dreamlike"
  ]
}
```

---

## Social Class

```json
{
  "id": "theme_class_conflict",
  "name": "class_conflict",
  "display_name_ko": "계급 갈등",
  "children": [
    "poverty",
    "wealth_gap",
    "social_mobility"
  ],
  "related_themes": [
    "capitalism",
    "power",
    "survival"
  ],
  "related_moods": [
    "tense",
    "realistic",
    "angry"
  ]
}
```

---

## Isolation

```json
{
  "id": "theme_isolation",
  "name": "isolation",
  "display_name_ko": "고립",
  "children": [
    "social_isolation",
    "emotional_isolation",
    "physical_isolation"
  ],
  "related_themes": [
    "loneliness",
    "fear",
    "identity"
  ],
  "related_moods": [
    "claustrophobic",
    "quiet",
    "anxious"
  ]
}
```

---

# Mood Ontology

```json
[
  {
    "name": "melancholic",
    "display_name_ko": "우울한"
  },
  {
    "name": "warm",
    "display_name_ko": "따뜻한"
  },
  {
    "name": "dark",
    "display_name_ko": "어두운"
  },
  {
    "name": "suspenseful",
    "display_name_ko": "긴장감있는"
  },
  {
    "name": "philosophical",
    "display_name_ko": "철학적인"
  },
  {
    "name": "surreal",
    "display_name_ko": "초현실적"
  },
  {
    "name": "bittersweet",
    "display_name_ko": "씁쓸한"
  },
  {
    "name": "dreamlike",
    "display_name_ko": "몽환적인"
  }
]
```

---

# Narrative Device Ontology

```json
[
  {
    "name": "time_loop",
    "display_name_ko": "타임루프"
  },
  {
    "name": "unreliable_narrator",
    "display_name_ko": "신뢰할 수 없는 화자"
  },
  {
    "name": "nonlinear_timeline",
    "display_name_ko": "비선형 구조"
  },
  {
    "name": "parallel_world",
    "display_name_ko": "평행세계"
  },
  {
    "name": "found_footage",
    "display_name_ko": "파운드 푸티지"
  }
]
```

---

# Neo4j Recommended Schema

## Nodes

```text
(:Movie)
(:Genre)
(:Theme)
(:Mood)
(:NarrativeDevice)
(:Keyword)
(:Country)
(:Person)
```

---

## Relationships

```text
(:Movie)-[:HAS_GENRE]->(:Genre)
(:Movie)-[:HAS_THEME]->(:Theme)
(:Movie)-[:HAS_MOOD]->(:Mood)
(:Movie)-[:USES_DEVICE]->(:NarrativeDevice)
(:Theme)-[:RELATED_TO]->(:Theme)
(:Genre)-[:RELATED_TO]->(:Genre)
```

---

# Example Movie Mapping

## Parasite

```json
{
  "title": "Parasite",
  "genres": [
    "drama",
    "thriller"
  ],
  "themes": [
    "class_conflict",
    "survival",
    "family"
  ],
  "moods": [
    "dark",
    "tense",
    "realistic"
  ],
  "narrative_devices": [
    "social_satire"
  ]
}
```

---

## Drive My Car

```json
{
  "title": "Drive My Car",
  "genres": [
    "drama"
  ],
  "themes": [
    "loss",
    "memory",
    "emotional_distance"
  ],
  "moods": [
    "quiet",
    "melancholic",
    "introspective"
  ],
  "narrative_devices": [
    "slow_cinema"
  ]
}
```

---

# Recommendation Engineering Tips

## 중요한 점

Genre 기반 추천은 매우 약합니다.

실제 추천 품질은:

```text
Theme
Mood
Narrative Device
Emotional Progression
Symbolic Pattern
```

이 결정합니다.

---

# 추천 우선순위

```text
1. Theme similarity
2. Mood similarity
3. Narrative similarity
4. Genre similarity
5. Social similarity
```

---

# 추천하는 추가 확장

## 추가 가능한 ontology

```text
Symbol
Visual Style
Color Tone
Cinematography
Pacing
Dialogue Density
Character Energy
Violence Level
Emotional Intensity
Philosophical Depth
```

---

# 추천 전략

## Explicit Semantic Graph

```text
User
→ likes existentialism
→ likes melancholic mood
→ likes slow pacing
→ recommends Drive My Car
```

## Embedding Only 방식은 비추천

반드시:

```text
Explicit Semantic Node
+
Embedding
```

혼합 구조를 권장.

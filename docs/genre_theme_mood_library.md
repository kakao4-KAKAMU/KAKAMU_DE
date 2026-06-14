# Movie Genre & Theme Ontology Dataset

## 목적

영화 추천 시스템, Neo4j Knowledge Graph, Semantic Retrieval, LLM Ontology Mapping에 활용 가능한 엔터프라이즈급 Genre/Theme 데이터셋.

구성 목표:

- 장르 정규화
- Theme ontology 구성
- 상위/하위 관계 정의
- Mood 연결
- Narrative Device 연결
- 추천 similarity 계산 가능 구조

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

## Science Fiction

```json
{
  "id": "genre_science_fiction",
  "name": "science_fiction",
  "display_name_ko": "SF",
  "related_genres": [
    "fantasy",
    "thriller",
    "science"
  ],
  "common_themes": [
    "humanity",
    "technology",
    "identity",
    "artificial_intelligence"
  ],
  "common_moods": [
    "futuristic",
    "philosophical",
    "surreal"
  ]
}
```

---

## Family

```json
{
  "id": "genre_family",
  "name": "family",
  "display_name_ko": "가족",
  "related_genres": [
    "drama",
    "comedy",
    "children"
  ],
  "common_themes": [
    "family",
    "love",
    "responsibility",
    "personal_growth"
  ],
  "common_moods": [
    "warm",
    "emotional",
    "bittersweet"
  ]
}
```

---

## Gangster

```json
{
  "id": "genre_gangster",
  "name": "gangster",
  "display_name_ko": "갱스터",
  "related_genres": [
    "crime",
    "noir",
    "drama"
  ],
  "common_themes": [
    "power",
    "betrayal",
    "loyalty",
    "corruption"
  ],
  "common_moods": [
    "gritty",
    "dark",
    "violent"
  ]
}
```

---

## Enlightenment

```json
{
  "id": "genre_enlightenment",
  "name": "enlightenment",
  "display_name_ko": "계몽",
  "related_genres": [
    "documentary",
    "education",
    "social"
  ],
  "common_themes": [
    "social_change",
    "justice",
    "awareness"
  ],
  "common_moods": [
    "hopeful",
    "inspiring",
    "serious"
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
    "horror_explicit",
    "mystery"
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

## Horror Explicit

```json
{
  "id": "genre_horror_explicit",
  "name": "horror_explicit",
  "display_name_ko": "공포(호러)",
  "related_genres": [
    "horror",
    "thriller"
  ],
  "common_themes": [
    "fear",
    "death",
    "survival"
  ],
  "common_moods": [
    "disturbing",
    "anxious",
    "violent"
  ]
}
```

---

## Science

```json
{
  "id": "genre_science",
  "name": "science",
  "display_name_ko": "과학",
  "related_genres": [
    "documentary",
    "science_fiction",
    "education"
  ],
  "common_themes": [
    "discovery",
    "technology",
    "humanity"
  ],
  "common_moods": [
    "curious",
    "philosophical",
    "wonder"
  ]
}
```

---

## Education

```json
{
  "id": "genre_education",
  "name": "education",
  "display_name_ko": "교육",
  "related_genres": [
    "documentary",
    "children",
    "social"
  ],
  "common_themes": [
    "personal_growth",
    "awareness",
    "responsibility"
  ],
  "common_moods": [
    "hopeful",
    "warm",
    "serious"
  ]
}
```

---

## Military

```json
{
  "id": "genre_military",
  "name": "military",
  "display_name_ko": "군사",
  "related_genres": [
    "war",
    "action",
    "espionage"
  ],
  "common_themes": [
    "duty",
    "sacrifice",
    "survival",
    "patriotism"
  ],
  "common_moods": [
    "tense",
    "intense",
    "serious"
  ]
}
```

---

## Christian Animation

```json
{
  "id": "genre_christian_animation",
  "name": "christian_animation",
  "display_name_ko": "기독교 애니메이션",
  "related_genres": [
    "animation",
    "children",
    "religion"
  ],
  "common_themes": [
    "faith",
    "redemption",
    "family"
  ],
  "common_moods": [
    "warm",
    "hopeful",
    "gentle"
  ]
}
```

---

## Documentary

```json
{
  "id": "genre_documentary",
  "name": "documentary",
  "display_name_ko": "기록",
  "related_genres": [
    "culture",
    "nature",
    "historical"
  ],
  "common_themes": [
    "truth",
    "memory",
    "identity"
  ],
  "common_moods": [
    "realistic",
    "quiet",
    "serious"
  ]
}
```

---

## Institutional

```json
{
  "id": "genre_institutional",
  "name": "institutional",
  "display_name_ko": "기업ㆍ기관ㆍ단체",
  "related_genres": [
    "documentary",
    "social",
    "culture"
  ],
  "common_themes": [
    "power",
    "corruption",
    "responsibility"
  ],
  "common_moods": [
    "serious",
    "realistic",
    "tense"
  ]
}
```

---

## Noir

```json
{
  "id": "genre_noir",
  "name": "noir",
  "display_name_ko": "느와르",
  "related_genres": [
    "crime",
    "thriller",
    "mystery"
  ],
  "common_themes": [
    "morality",
    "betrayal",
    "obsession",
    "corruption"
  ],
  "common_moods": [
    "dark",
    "gritty",
    "melancholic"
  ]
}
```

---

## Multi Part

```json
{
  "id": "genre_multi_part",
  "name": "multi_part",
  "display_name_ko": "다부작",
  "related_genres": [
    "serial",
    "drama",
    "historical"
  ],
  "common_themes": [
    "destiny",
    "family",
    "personal_growth"
  ],
  "common_moods": [
    "epic",
    "emotional",
    "nostalgic"
  ]
}
```

---

## Lgbtq

```json
{
  "id": "genre_lgbtq",
  "name": "lgbtq",
  "display_name_ko": "동성애",
  "related_genres": [
    "drama",
    "romance",
    "youth"
  ],
  "common_themes": [
    "identity",
    "love",
    "isolation",
    "acceptance"
  ],
  "common_moods": [
    "emotional",
    "bittersweet",
    "warm"
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
    "social"
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

## Road Movie

```json
{
  "id": "genre_road_movie",
  "name": "road_movie",
  "display_name_ko": "로드무비",
  "related_genres": [
    "drama",
    "adventure",
    "comedy"
  ],
  "common_themes": [
    "self_discovery",
    "freedom",
    "friendship"
  ],
  "common_moods": [
    "nostalgic",
    "hopeful",
    "bittersweet"
  ]
}
```

---

## Romance

```json
{
  "id": "genre_romance",
  "name": "romance",
  "display_name_ko": "멜로/로맨스",
  "related_genres": [
    "drama",
    "comedy",
    "melodrama"
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

## Melodrama

```json
{
  "id": "genre_melodrama",
  "name": "melodrama",
  "display_name_ko": "멜로드라마",
  "related_genres": [
    "drama",
    "romance",
    "shinpa"
  ],
  "common_themes": [
    "love",
    "loss",
    "family",
    "sacrifice"
  ],
  "common_moods": [
    "emotional",
    "melancholic",
    "tragic"
  ]
}
```

---

## Adventure

```json
{
  "id": "genre_adventure",
  "name": "adventure",
  "display_name_ko": "모험",
  "related_genres": [
    "action",
    "fantasy",
    "adventure_epic"
  ],
  "common_themes": [
    "hero_journey",
    "survival",
    "friendship"
  ],
  "common_moods": [
    "epic",
    "wonder",
    "adrenaline"
  ]
}
```

---

## Wuxia

```json
{
  "id": "genre_wuxia",
  "name": "wuxia",
  "display_name_ko": "무협",
  "related_genres": [
    "action",
    "period_drama",
    "fantasy"
  ],
  "common_themes": [
    "justice",
    "revenge",
    "honor",
    "destiny"
  ],
  "common_moods": [
    "epic",
    "intense",
    "mythical"
  ]
}
```

---

## Literary

```json
{
  "id": "genre_literary",
  "name": "literary",
  "display_name_ko": "문예",
  "related_genres": [
    "drama",
    "art",
    "historical"
  ],
  "common_themes": [
    "identity",
    "memory",
    "loss"
  ],
  "common_moods": [
    "melancholic",
    "quiet",
    "philosophical"
  ]
}
```

---

## Culture

```json
{
  "id": "genre_culture",
  "name": "culture",
  "display_name_ko": "문화",
  "related_genres": [
    "documentary",
    "art",
    "regional"
  ],
  "common_themes": [
    "identity",
    "memory",
    "tradition"
  ],
  "common_moods": [
    "nostalgic",
    "warm",
    "quiet"
  ]
}
```

---

## Musical

```json
{
  "id": "genre_musical",
  "name": "musical",
  "display_name_ko": "뮤지컬",
  "related_genres": [
    "music",
    "romance",
    "comedy"
  ],
  "common_themes": [
    "love",
    "dream",
    "personal_growth"
  ],
  "common_moods": [
    "joyful",
    "hopeful",
    "warm"
  ]
}
```

---

## Music

```json
{
  "id": "genre_music",
  "name": "music",
  "display_name_ko": "뮤직",
  "related_genres": [
    "musical",
    "biopic",
    "documentary"
  ],
  "common_themes": [
    "identity",
    "passion",
    "dream"
  ],
  "common_moods": [
    "energetic",
    "emotional",
    "nostalgic"
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
    "noir"
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

## Division

```json
{
  "id": "genre_division",
  "name": "division",
  "display_name_ko": "반공/분단",
  "related_genres": [
    "war",
    "drama",
    "historical"
  ],
  "common_themes": [
    "identity",
    "family",
    "survival",
    "loss"
  ],
  "common_moods": [
    "tragic",
    "tense",
    "melancholic"
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
    "noir"
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

## Social

```json
{
  "id": "genre_social",
  "name": "social",
  "display_name_ko": "사회",
  "related_genres": [
    "drama",
    "documentary",
    "social_realism"
  ],
  "common_themes": [
    "class_conflict",
    "justice",
    "survival"
  ],
  "common_moods": [
    "realistic",
    "tense",
    "serious"
  ]
}
```

---

## Social Realism

```json
{
  "id": "genre_social_realism",
  "name": "social_realism",
  "display_name_ko": "사회물(경향)",
  "related_genres": [
    "social",
    "drama",
    "noir"
  ],
  "common_themes": [
    "class_conflict",
    "corruption",
    "survival"
  ],
  "common_moods": [
    "gritty",
    "dark",
    "realistic"
  ]
}
```

---

## Western

```json
{
  "id": "genre_western",
  "name": "western",
  "display_name_ko": "서부",
  "related_genres": [
    "action",
    "adventure",
    "crime"
  ],
  "common_themes": [
    "justice",
    "revenge",
    "survival"
  ],
  "common_moods": [
    "gritty",
    "epic",
    "tense"
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

## Sports

```json
{
  "id": "genre_sports",
  "name": "sports",
  "display_name_ko": "스포츠",
  "related_genres": [
    "drama",
    "youth",
    "biopic"
  ],
  "common_themes": [
    "personal_growth",
    "teamwork",
    "perseverance"
  ],
  "common_moods": [
    "inspiring",
    "intense",
    "hopeful"
  ]
}
```

---

## Period Drama

```json
{
  "id": "genre_period_drama",
  "name": "period_drama",
  "display_name_ko": "시대극/사극",
  "related_genres": [
    "historical",
    "drama",
    "wuxia"
  ],
  "common_themes": [
    "power",
    "honor",
    "destiny",
    "family"
  ],
  "common_moods": [
    "epic",
    "melancholic",
    "mythical"
  ]
}
```

---

## Shinpa

```json
{
  "id": "genre_shinpa",
  "name": "shinpa",
  "display_name_ko": "신파",
  "related_genres": [
    "melodrama",
    "drama",
    "family"
  ],
  "common_themes": [
    "love",
    "loss",
    "sacrifice",
    "family"
  ],
  "common_moods": [
    "emotional",
    "tragic",
    "melancholic"
  ]
}
```

---

## Experimental

```json
{
  "id": "genre_experimental",
  "name": "experimental",
  "display_name_ko": "실험",
  "related_genres": [
    "art",
    "drama",
    "documentary"
  ],
  "common_themes": [
    "identity",
    "alienation",
    "absurdity"
  ],
  "common_moods": [
    "surreal",
    "dreamlike",
    "philosophical"
  ]
}
```

---

## Children

```json
{
  "id": "genre_children",
  "name": "children",
  "display_name_ko": "아동",
  "related_genres": [
    "family",
    "animation",
    "fantasy"
  ],
  "common_themes": [
    "friendship",
    "personal_growth",
    "courage"
  ],
  "common_moods": [
    "warm",
    "hopeful",
    "lighthearted"
  ]
}
```

---

## Animation

```json
{
  "id": "genre_animation",
  "name": "animation",
  "display_name_ko": "애니메이션",
  "related_genres": [
    "fantasy",
    "family",
    "children"
  ],
  "common_themes": [
    "hero_journey",
    "friendship",
    "identity"
  ],
  "common_moods": [
    "wonder",
    "warm",
    "lighthearted"
  ]
}
```

---

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

## Adventure Epic

```json
{
  "id": "genre_adventure_epic",
  "name": "adventure_epic",
  "display_name_ko": "어드벤처",
  "related_genres": [
    "adventure",
    "fantasy",
    "action"
  ],
  "common_themes": [
    "hero_journey",
    "destiny",
    "survival"
  ],
  "common_moods": [
    "epic",
    "wonder",
    "adrenaline"
  ]
}
```

---

## Erotica

```json
{
  "id": "genre_erotica",
  "name": "erotica",
  "display_name_ko": "에로",
  "related_genres": [
    "drama",
    "romance"
  ],
  "common_themes": [
    "desire",
    "obsession",
    "identity"
  ],
  "common_moods": [
    "sensual",
    "dark",
    "intense"
  ]
}
```

---

## Historical

```json
{
  "id": "genre_historical",
  "name": "historical",
  "display_name_ko": "역사",
  "related_genres": [
    "period_drama",
    "war",
    "biopic"
  ],
  "common_themes": [
    "power",
    "memory",
    "identity"
  ],
  "common_moods": [
    "epic",
    "serious",
    "melancholic"
  ]
}
```

---

## Serial

```json
{
  "id": "genre_serial",
  "name": "serial",
  "display_name_ko": "연쇄극",
  "related_genres": [
    "multi_part",
    "drama",
    "thriller"
  ],
  "common_themes": [
    "obsession",
    "destiny",
    "family"
  ],
  "common_moods": [
    "suspenseful",
    "emotional",
    "nostalgic"
  ]
}
```

---

## Art

```json
{
  "id": "genre_art",
  "name": "art",
  "display_name_ko": "예술",
  "related_genres": [
    "experimental",
    "biopic",
    "literary"
  ],
  "common_themes": [
    "identity",
    "passion",
    "alienation"
  ],
  "common_moods": [
    "dreamlike",
    "melancholic",
    "philosophical"
  ]
}
```

---

## Omnibus

```json
{
  "id": "genre_omnibus",
  "name": "omnibus",
  "display_name_ko": "옴니버스",
  "related_genres": [
    "drama",
    "comedy",
    "experimental"
  ],
  "common_themes": [
    "identity",
    "daily_life",
    "connection"
  ],
  "common_moods": [
    "bittersweet",
    "varied",
    "quiet"
  ]
}
```

---

## Human Rights

```json
{
  "id": "genre_human_rights",
  "name": "human_rights",
  "display_name_ko": "인권",
  "related_genres": [
    "documentary",
    "social",
    "drama"
  ],
  "common_themes": [
    "justice",
    "survival",
    "responsibility"
  ],
  "common_moods": [
    "serious",
    "emotional",
    "hopeful"
  ]
}
```

---

## Portrait

```json
{
  "id": "genre_portrait",
  "name": "portrait",
  "display_name_ko": "인물",
  "related_genres": [
    "biopic",
    "documentary",
    "historical"
  ],
  "common_themes": [
    "identity",
    "legacy",
    "memory"
  ],
  "common_moods": [
    "inspiring",
    "serious",
    "emotional"
  ]
}
```

---

## Nature

```json
{
  "id": "genre_nature",
  "name": "nature",
  "display_name_ko": "자연ㆍ환경",
  "related_genres": [
    "documentary",
    "adventure",
    "disaster"
  ],
  "common_themes": [
    "survival",
    "responsibility",
    "wonder"
  ],
  "common_moods": [
    "awe",
    "quiet",
    "hopeful"
  ]
}
```

---

## Disaster

```json
{
  "id": "genre_disaster",
  "name": "disaster",
  "display_name_ko": "재난",
  "related_genres": [
    "action",
    "thriller",
    "science_fiction"
  ],
  "common_themes": [
    "survival",
    "fear",
    "family"
  ],
  "common_moods": [
    "intense",
    "tense",
    "anxious"
  ]
}
```

---

## Biopic

```json
{
  "id": "genre_biopic",
  "name": "biopic",
  "display_name_ko": "전기",
  "related_genres": [
    "drama",
    "historical",
    "portrait"
  ],
  "common_themes": [
    "identity",
    "legacy",
    "personal_growth"
  ],
  "common_moods": [
    "inspiring",
    "emotional",
    "serious"
  ]
}
```

---

## War

```json
{
  "id": "genre_war",
  "name": "war",
  "display_name_ko": "전쟁",
  "related_genres": [
    "military",
    "historical",
    "drama"
  ],
  "common_themes": [
    "survival",
    "loss",
    "sacrifice",
    "morality"
  ],
  "common_moods": [
    "intense",
    "tragic",
    "dark"
  ]
}
```

---

## Religion

```json
{
  "id": "genre_religion",
  "name": "religion",
  "display_name_ko": "종교",
  "related_genres": [
    "drama",
    "historical",
    "documentary"
  ],
  "common_themes": [
    "faith",
    "redemption",
    "morality"
  ],
  "common_moods": [
    "serious",
    "hopeful",
    "philosophical"
  ]
}
```

---

## Regional

```json
{
  "id": "genre_regional",
  "name": "regional",
  "display_name_ko": "지역",
  "related_genres": [
    "culture",
    "drama",
    "documentary"
  ],
  "common_themes": [
    "identity",
    "tradition",
    "community"
  ],
  "common_moods": [
    "nostalgic",
    "warm",
    "quiet"
  ]
}
```

---

## Espionage

```json
{
  "id": "genre_espionage",
  "name": "espionage",
  "display_name_ko": "첩보",
  "related_genres": [
    "thriller",
    "action",
    "crime"
  ],
  "common_themes": [
    "conspiracy",
    "betrayal",
    "survival"
  ],
  "common_moods": [
    "suspenseful",
    "tense",
    "dark"
  ]
}
```

---

## Youth

```json
{
  "id": "genre_youth",
  "name": "youth",
  "display_name_ko": "청춘영화",
  "related_genres": [
    "drama",
    "romance",
    "teen"
  ],
  "common_themes": [
    "personal_growth",
    "identity",
    "friendship"
  ],
  "common_moods": [
    "hopeful",
    "nostalgic",
    "bittersweet"
  ]
}
```

---

## Comedy

```json
{
  "id": "genre_comedy",
  "name": "comedy",
  "display_name_ko": "코메디",
  "related_genres": [
    "romance",
    "family",
    "teen"
  ],
  "common_themes": [
    "friendship",
    "daily_life",
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

## Fantasy

```json
{
  "id": "genre_fantasy",
  "name": "fantasy",
  "display_name_ko": "판타지",
  "related_genres": [
    "adventure",
    "science_fiction",
    "animation"
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

## Teen

```json
{
  "id": "genre_teen",
  "name": "teen",
  "display_name_ko": "하이틴(고교)",
  "related_genres": [
    "youth",
    "romance",
    "comedy"
  ],
  "common_themes": [
    "identity",
    "friendship",
    "first_love"
  ],
  "common_moods": [
    "hopeful",
    "lighthearted",
    "nostalgic"
  ]
}
```

---

## Adaptation

```json
{
  "id": "genre_adaptation",
  "name": "adaptation",
  "display_name_ko": "합작(번안물)",
  "related_genres": [
    "drama",
    "historical",
    "romance"
  ],
  "common_themes": [
    "identity",
    "cultural_exchange",
    "love"
  ],
  "common_moods": [
    "varied",
    "emotional",
    "nostalgic"
  ]
}
```

---

## Naval Action

```json
{
  "id": "genre_naval_action",
  "name": "naval_action",
  "display_name_ko": "해양액션",
  "related_genres": [
    "action",
    "war",
    "adventure"
  ],
  "common_themes": [
    "survival",
    "heroism",
    "duty"
  ],
  "common_moods": [
    "intense",
    "adrenaline",
    "epic"
  ]
}
```

---

## Period Action

```json
{
  "id": "genre_period_action",
  "name": "period_action",
  "display_name_ko": "활극",
  "related_genres": [
    "action",
    "wuxia",
    "period_drama"
  ],
  "common_themes": [
    "justice",
    "revenge",
    "honor"
  ],
  "common_moods": [
    "epic",
    "intense",
    "adrenaline"
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
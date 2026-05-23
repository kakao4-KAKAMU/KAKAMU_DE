# Movie Recommend System (GraphRAG)

> Neo4j + LangGraph + LangChain + FastAPI + vLLM 기반 **지식그래프 영화/피드 추천 + LLM Chat** 시스템.
> 비정형(영화 줄거리·피드·댓글)을 **온톨로지** 로 표상해 Neo4j 에 적재하고,
> semantic × keyword × graph 하이브리드 추천을 수행한다.

---

## 1. 폴더 구조

```
movie_recommand_system/
├── README.md
├── requirements.txt
├── docs/
│   ├── architecture.md          # 시스템 아키텍처 (Mermaid)
│   ├── neo4j_schema.md          # Neo4j 노드/관계/인덱스 (Mermaid)
│   └── ontology.md              # 온톨로지 매핑 정책
├── scripts/
│   └── bootstrap_schema.py      # Neo4j + Postgres 스키마 초기화
└── src/
    ├── config/settings.py       # Pydantic Settings (Neo4j/PG/vLLM/Embedding)
    ├── ontology/
    │   ├── schema.py            # MoviePlot/Feed/Comment Ontology (Pydantic)
    │   └── prompts.py           # ★ 온톨로지 매핑 프롬프트 (핵심)
    ├── graph/
    │   ├── cypher_statements.py # 제약/인덱스/벡터인덱스/Upsert/Hybrid 쿼리
    │   ├── client.py            # Neo4j 드라이버 래퍼
    │   └── loader.py            # Ontology → Neo4j Upsert
    ├── extractor/
    │   ├── base.py              # OntologyExtractor 추상화
    │   ├── movie_extractor.py
    │   ├── feed_extractor.py
    │   └── comment_extractor.py
    ├── llm/
    │   └── vllm_client.py       # OpenAI-호환 vLLM 클라이언트 (KV-cache friendly)
    ├── persistence/
    │   └── chat_history.py      # PostgreSQL 채팅 이력 스토어
    └── api/                     # FastAPI 라우터 (추후 확장 지점)
```

---

## 2. 핵심 책임 (SOLID 매핑)

| 책임 | 모듈 | 원칙 |
|------|------|------|
| 비정형 → 온톨로지 변환 | `ontology/prompts.py`, `extractor/*` | SRP / DIP |
| 표상 검증 | `ontology/schema.py` (Pydantic) | LSP |
| 그래프 스키마 정의 | `graph/cypher_statements.py` | OCP (추가만으로 확장) |
| 그래프 IO | `graph/client.py`, `graph/loader.py` | SRP / DIP |
| LLM 호출 | `llm/vllm_client.py` | LSP (LLMClient Protocol) |
| 채팅 이력 영속화 | `persistence/chat_history.py` | SRP |
| 설정 | `config/settings.py` | ISP (도메인별 Settings 분리) |

---

## 3. Quick Start

### 3-1. Neo4j 실행 (`GraphRAG/Neo4j.md` 참고)

```bash
docker run --rm -p 7474:7474 -p 7687:7687 \
  -v ~/Desktop/dvc/chatbot/neo4j/data:/data \
  -v ~/Desktop/dvc/chatbot/neo4j/plugins:/var/lib/neo4j/plugins \
  -v ~/Desktop/dvc/chatbot/neo4j/conf:/var/lib/neo4j/conf \
  -e NEO4J_apoc_export_file_enabled=true \
  -e NEO4J_apoc_import_file_enabled=true \
  -e NEO4J_PLUGINS='["apoc-extended"]' \
  neo4j:5
```

### 3-2. vLLM 실행 (T4 16GB: gen + embed 동시)

```bash
./scripts/start_vllm.sh
# Generation: Qwen2.5-7B-Instruct-AWQ @ :8000 (gpu 65%)
# Embedding:  BAAI/bge-m3 @ :8001 (gpu 20%)
```

### 3-3. 의존성 / 스키마

```bash
pip install -r requirements.txt

# Neo4j 제약·인덱스·벡터인덱스 + Postgres 채팅 이력 스키마 일괄 적용
python -m scripts.bootstrap_schema
```

### 3-4. 환경변수 예시 (`.env`)

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=dlsghks12
NEO4J_DATABASE=neo4j

PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=chatbot
PG_USER=postgres
PG_PASSWORD=postgres

VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
VLLM_ENABLE_PREFIX_CACHING=true

EMBED_MODEL_NAME=BAAI/bge-m3
EMBED_DIMENSION=1024
```

---

## 4. 온톨로지 매핑 프롬프트 (요약)

`src/ontology/prompts.py` 가 본 프로젝트의 **핵심 자산**이다.

- `ONTOLOGY_SYSTEM_PROMPT` (상수)
  - 출력 형식(JSON only), 환각 금지, 정규화 규칙, semantic/keyword 균형 규칙을 강제.
  - **모든 호출에서 동일한 prefix** 라 vLLM prefix-cache 가 재사용된다.
- `build_movie_plot_messages(...)`
  - 영화 메타 + 줄거리 → `MoviePlotOntology`
  - `summary / themes / moods / tropes / keywords / characters / locations / target_audience` 추출.
- `build_feed_messages(...)`
  - 피드 본문 → `FeedOntology`
  - `categories / sentiment / sentiment_score / emotions / keywords / referenced_movie_ids / contains_spoiler / toxicity_score` 추출.
- `build_comment_messages(...)`
  - 댓글 본문 → `CommentOntology`
  - `intents / sentiment / emotions / keywords / targets_user_id / contains_spoiler / toxicity_score` 추출.
- `build_user_intent_messages(...)`
  - 사용자 자연어 추천 요청 → 단일 Cypher 쿼리(JSON) 변환.

> 사용 예
> ```python
> from src.llm.vllm_client import VLLMChatClient
> from src.extractor.movie_extractor import MoviePlotExtractor
>
> llm = VLLMChatClient()
> ext = MoviePlotExtractor(llm)
> ontology = ext.extract(
>     movie_id="m-001",
>     title="기생충",
>     producing_year=2019,
>     country="KR",
>     genres=["드라마", "스릴러"],
>     plot="전원백수 가족이 부유한 가족의 집에 한 명씩 침투하기 시작하면서...",
> )
> ```

---

## 5. 추천 알고리즘 한눈에

`HYBRID_MOVIE_RECOMMEND` (`src/graph/cypher_statements.py`) 의 가중합:

```
score = 0.55 · vector_similarity
      + 0.15 · (1 - exp(-keyword_hits))
      + 0.10 · (1 - exp(-theme_hits))
      + 0.05 · (1 - exp(-mood_hits))
      + 0.15 · tanh(user_pref_score)
```

- **vector_similarity** : `plot_embedding` 의 cosine 유사도 → semantic
- **keyword/theme/mood** : 사용자 질의에서 추출된 정규화 표제어 매칭 → keyword
- **user_pref_score** : `(:User)-[:PREFERS]->(:Genre|:Theme|:Keyword)` 누적치

상세는 `docs/architecture.md` §5 참고.

---

## 6. 운영 가이드 (요지)

- vLLM 은 반드시 `--enable-prefix-caching` 옵션과 함께 기동한다.
- 시스템 프롬프트(`ONTOLOGY_SYSTEM_PROMPT`)는 **불변 상수** 로 둔다 (KV-cache 재사용).
- 사용자별 chat history 는 PostgreSQL `chat_message` 테이블에 적재한다.
- 임베딩 모델을 교체할 경우 `EMBED_DIMENSION` 을 갱신한 뒤
  `scripts/bootstrap_schema.py` 를 재실행해야 벡터 인덱스가 재정의된다.
- 신규 카테고리/감정 태그를 추가하려면
  1) `ontology/schema.py` 의 Enum 에 추가,
  2) `graph/cypher_statements.py` 의 `SEED_*` 에 추가,
  3) `bootstrap_schema` 재실행.

---

## 7. 다음 단계 (Roadmap)

- [ ] LangGraph `StateGraph` 로 추천 워크플로우 구성 (`src/api/` 라우터 포함)
- [ ] 임베딩 모듈 추상화 (`src/embedding/`) 및 캐시 적용
- [ ] LangGraph `PostgresSaver` 로 LangGraph 체크포인트 영속화 통합
- [ ] 평가 데이터셋 + Recall@K / NDCG 지표 자동화

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
├── docs/                        # 설계·운영 문서 (§7 참고)
├── scripts/
│   ├── bootstrap_schema.py      # Neo4j + Postgres 스키마 초기화
│   ├── run_ingest_worker.py     # Outbox worker (production / mock)
│   ├── start_vllm.sh            # vLLM gen(:8000) + embed(:8001)
│   ├── embed_migrate.py         # 임베딩 버전 등록·re-embed·승격
│   ├── seed_vocab_from_library.py
│   └── build_goldenset.py
└── src/
    ├── config/settings.py       # Pydantic Settings (도메인별 분리)
    ├── api/                     # FastAPI 게이트웨이 (Chat/Recommend/Ingest/Feedback)
    ├── chat/                    # LangGraph StateGraph + Cypher tool
    ├── recommend/               # Bandit 정책, IntentResolver, reward
    ├── ontology/
    │   ├── schema.py            # MoviePlot/Feed/Comment Ontology (Pydantic)
    │   └── prompts/             # ★ 온톨로지·답변 프롬프트 (핵심)
    ├── graph/
    │   ├── cypher_statements/   # 제약/인덱스/벡터/Upsert/Hybrid 쿼리
    │   ├── template_registry.py # Cypher Template 화이트리스트
    │   ├── template_executor.py
    │   ├── templates/           # hybrid_recommend, hybrid_feed_recommend
    │   ├── client.py            # Neo4j 드라이버 래퍼
    │   └── loader.py            # Ontology → Neo4j Upsert
    ├── extractor/               # OntologyExtractor + 도메인별 추출기
    ├── embedding/               # 버전드 임베딩, dual-write, re-embed
    ├── ingest/                  # Outbox worker + aggregate dispatcher
    ├── vocab/                   # 자동 어휘 정규화·승격
    ├── eval/                    # LLM Judge, drift 감지
    ├── llm/vllm_client.py       # OpenAI-호환 vLLM 클라이언트
    └── persistence/             # PostgreSQL (chat, outbox, eval, bandit)
```

---

## 2. 핵심 책임 (SOLID 매핑)

| 책임 | 모듈 | 원칙 |
|------|------|------|
| 비정형 → 온톨로지 변환 | `ontology/prompts/`, `extractor/*` | SRP / DIP |
| 표상 검증 | `ontology/schema.py` (Pydantic) | LSP |
| 그래프 스키마·쿼리 | `graph/cypher_statements/` | OCP (추가만으로 확장) |
| 추천 Cypher 실행 | `graph/templates/`, `template_executor.py` | SRP / 화이트리스트 |
| Chat Cypher 조회 | `chat/cypher/service.py` (GraphCypherQAChain) | SRP |
| 그래프 IO | `graph/client.py`, `graph/loader.py` | SRP / DIP |
| LLM 호출 | `llm/vllm_client.py` | LSP (LLMClient Protocol) |
| 채팅·Bandit·Outbox | `persistence/*`, `chat/`, `recommend/` | SRP |
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
# Generation: Qwen3-8B-GGUF @ :8000 (gpu 65%)
# Embedding:  Qwen3-Embedding-0.6B @ :8001 (gpu 20%)
```

### 3-3. 의존성 / 스키마

```bash
pip install -r requirements.txt

# Neo4j 제약·인덱스·벡터인덱스 + Postgres (chat/outbox/eval/bandit/checkpoint) 일괄 적용
python -m scripts.bootstrap_schema
python scripts/seed_vocab_from_library.py   # Genre/Theme/Mood 시드 (선택)
```

### 3-4. 환경변수 예시 (`.env`)

`.env.example` 을 복사해 사용한다. 주요 항목:

```dotenv
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4j

PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=chatbot
PG_USER=postgres
PG_PASSWORD=postgres

VLLM_GEN__BASE_URL=http://localhost:8000/v1
VLLM_GEN__MODEL_NAME=Qwen/Qwen3-8B-GGUF:Q4_K_M
VLLM_GEN__ENABLE_PREFIX_CACHING=true

VLLM_EMBED__BASE_URL=http://localhost:8001/v1
VLLM_EMBED__MODEL_NAME=Qwen/Qwen3-Embedding-0.6B

EMBED__DIMENSION=1024
EMBED__NORMALIZE=true

ONTOLOGY_PROMPT_VERSION=1.0
BANDIT_BASELINE_MIN_SHARE=0.05
```

---

## 4. 온톨로지 매핑 프롬프트 (요약)

`src/ontology/prompts/` 가 본 프로젝트의 **핵심 자산**이다.

- `ONTOLOGY_SYSTEM_PROMPT` (`prompts/base.py`)
  - 출력 형식(JSON only), 환각 금지, 정규화 규칙, semantic/keyword 균형 규칙을 강제.
  - **모든 호출에서 동일한 prefix** 라 vLLM prefix-cache 가 재사용된다.
- `build_movie_plot_messages(...)` — 영화 메타 + 줄거리 → `MoviePlotOntology`
- `build_feed_messages(...)` — 피드 본문 → `FeedOntology`
- `build_comment_messages(...)` — 댓글 본문 → `CommentOntology`
- `build_reply_messages(...)` — Chat structured reply (movie/feed/both/none)

> 사용 예
>
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

> **Persona** `(user_id, persona_id)` 가 추천의 최소 단위이다. 상세: [docs/persona_recommendation.md](docs/persona_recommendation.md)

`hybrid_recommend` / `hybrid_feed_recommend` Cypher (`src/graph/cypher_statements/retrieval.py`) 의 가중합:

```
score = w_vec · vector_similarity
      + w_kw  · (1 - exp(-keyword_hits))
      + w_theme · (1 - exp(-theme_hits))
      + w_mood  · (1 - exp(-mood_hits))
      + w_user  · tanh(persona_pref_score)   // persona_id 존재 시
```

- **vector_similarity** : `plot_embedding` / `summary_embedding` cosine 유사도 → semantic
- **keyword/theme/mood** : `IntentResolver` 가 질의에서 추출한 정규화 표제어 매칭 → keyword
- **persona_pref_score** : `(:Persona)-[:PREFERS]->(:Genre|:Theme|:Keyword)` 누적치
- **Bandit arm** : `w_*` 가중치는 Thompson Sampling 으로 `(user_id:persona_id)` 별 선택

상세는 `docs/architecture.md` §5 참고.

---

## 6. Chat 흐름 (LangGraph)

`src/chat/graph.py`:

```
embed_query → agent
    ├─ (tool_calls) → neo4j_tools → agent  (루프, max 15)
    └─ (no tools)   → persist_history → END
```

- **embed_query** : 질의 벡터화 (`VLLMEmbeddingClient`)
- **agent** : tool-calling LLM — 필요 시 `query_neo4j_graph` 호출
- **neo4j_tools** : `GraphCypherQAChain` + CyVer 검증 → `retrieved_movies/feeds` 병합
- **persist_history** : assistant 응답 + `ontology_ref` → PostgreSQL

HTTP API: `POST /chat/stream` (SSE). 상세: [docs/api.md](docs/api.md)

---

## 7. 구현 완료 모듈

| 영역 | 모듈 | 문서 |
|------|------|------|
| Cypher Template | `src/graph/template_*`, `templates/` | [docs/cypher_templates.md](docs/cypher_templates.md) |
| Versioned Embedding | `src/embedding/*` | [docs/versioned_embedding.md](docs/versioned_embedding.md) |
| Auto Vocabulary | `src/vocab/*` | [docs/auto_vocab.md](docs/auto_vocab.md) |
| Outbox Ingest | `src/ingest/*` | [docs/outbox_ingest.md](docs/outbox_ingest.md) |
| Bandit Weights | `src/recommend/*` | [docs/bandit_weights.md](docs/bandit_weights.md) |
| LLM Judge | `src/eval/*` | [docs/llm_judge.md](docs/llm_judge.md) |
| LangGraph + FastAPI | `src/chat/*`, `src/api/*` | [docs/api.md](docs/api.md) |
| Neo4j 스키마 | `src/graph/cypher_statements/schema.py` | [docs/neo4j_schema.md](docs/neo4j_schema.md) |
| 온톨로지 정책 | `src/ontology/*` | [docs/ontology.md](docs/ontology.md) |
| Genre/Theme/Mood | `docs/genre_theme_mood_library.md` | 시드·vocab 기준 데이터셋 |
| 아키텍처 | — | [docs/architecture.md](docs/architecture.md) |
| 기술 스택 요약 | — | [docs/tech_structure.md](docs/tech_structure.md) |

통합 smoke: [docs/smoke_test.md](docs/smoke_test.md)

---

## 8. 서비스 실행

```bash
# 1) 인프라 및 스키마 (Postgres / Neo4j / LangGraph checkpoint)
python -m scripts.bootstrap_schema

# 2) Outbox worker (실 Extractor + Loader)
python -m scripts.run_ingest_worker            # production
python -m scripts.run_ingest_worker --mock     # mock (smoke 용)

# 3) HTTP API
uvicorn src.api.app:app --host 0.0.0.0 --port 8080
```

OpenAPI: `http://localhost:8080/docs` (리버스 프록시 prefix: `/chat-api`)

---

## 9. 운영 가이드 (요지)

- vLLM 은 `--enable-prefix-caching` 옵션과 함께 기동한다.
- 시스템 프롬프트(`ONTOLOGY_SYSTEM_PROMPT`)는 **불변 상수** 로 둔다 (KV-cache 재사용).
- 사용자별 chat history 는 PostgreSQL `chat_message` 테이블에 적재한다.
- 임베딩 모델을 교체할 경우 `EMBED__DIMENSION` 을 갱신한 뒤
  `scripts/bootstrap_schema.py` 및 `scripts/embed_migrate.py` 를 실행한다.
- 신규 카테고리/감정 태그를 추가하려면
  1. `ontology/schema.py` 의 Enum 에 추가,
  2. `graph/cypher_statements/schema.py` 의 `SEED_*` 에 추가,
  3. `bootstrap_schema` 재실행.

---

## 10. 향후 (Backlog)

- GitHub Actions CI (`ruff` / `mypy` / `pytest`)
- structlog / prometheus exporter 본격 도입
- `tenacity` 기반 vLLM/Neo4j retry policy
- schema_version 마이그레이션 도구
- 한국어 도메인 goldenset 보강
- Neo4j MCP 연동 (`GraphRAG/index.ipynb`)

# 통합 Smoke Test 가이드

Tesla T4 16GB / 로컬 vLLM only / 동시 채팅 10명 기준.

---

## 1. 사전 준비

```bash
cd GraphRAG/movie_recommand_system
cp .env.example .env
pip install -r requirements.txt
pip install 'psycopg[binary]' pytest
```

---

## 2. 인프라 기동

```bash
# Neo4j (별도 터미널, GraphRAG/Neo4j.md 참고)
docker run --rm -p 7474:7474 -p 7687:7687 neo4j:5

# vLLM generation + embedding (T4 단일 GPU)
./scripts/start_vllm.sh

# Neo4j + Postgres 스키마 일괄 (outbox, eval, bandit, LangGraph checkpoint 포함)
python -m scripts.bootstrap_schema
python scripts/seed_vocab_from_library.py
```

---

## 3. 단위 테스트 (mock)

```bash
python -m pytest tests/ -q
```

---

## 4. Cypher Template smoke

```python
from src.graph.client import Neo4jClient
from src.graph.template_executor import TemplateExecutor
from src.graph.templates import build_default_registry

with Neo4jClient() as neo:
    ex = TemplateExecutor(build_default_registry(), neo)
    rows = ex.execute(
        "hybrid_recommend",
        {
            "user_id": "u-demo",
            "persona_id": "movie_buff",
            "query_embedding": [0.0] * 1024,
            "query_keywords": [],
            "query_themes": [],
            "query_moods": [],
            "top_k": 5,
            "vec_top_k": 20,
            "w_vec": 0.55,
            "w_kw": 0.15,
            "w_theme": 0.10,
            "w_mood": 0.05,
            "w_user": 0.15,
            "max_toxicity": 0.7,
        },
        fallback=False,
    )
    print(rows)
```

---

## 4-1. Persona Chat smoke (SSE)

```bash
# API 서버 기동 (별도 터미널)
uvicorn src.api.app:app --host 0.0.0.0 --port 8080

curl -N http://localhost:8080/chat/stream \
  -H 'content-type: application/json' \
  -H 'X-Persona-Id: movie_buff' \
  -d '{"user_id":"u-demo","message":"공포 영화 추천"}'
```

---

## 4-2. Recommend smoke

```bash
curl -s http://localhost:8080/recommend/movie \
  -H 'content-type: application/json' \
  -H 'X-Persona-Id: movie_buff' \
  -d '{"user_id":"u-demo","query":"잔잔한 가족 영화"}' | jq
```

---

## 5. Judge 1회 실행

```python
from src.eval.judge_runner import JudgeRunner

runner = JudgeRunner()
scores = runner.judge_one(
    source_id="m-demo",
    source_type="movie",
    raw_text="가족과 성장을 다룬 드라마",
    ontology={"summary": "가족 드라마", "themes": ["성장"], "sentiment": "neutral"},
)
print(scores)
```

---

## 6. Outbox worker (1 tick)

```bash
python -m scripts.run_ingest_worker --once
# mock dispatcher:
python -m scripts.run_ingest_worker --mock --once
```

---

## 7. 동시 10명 부하 (수동)

- `VLLM_GEN__MAX_NUM_SEQS=32` 유지
- 10개 병렬 curl 로 `/chat/stream` 호출 시 TTFT < 3s 목표
- OOM 시 `max-num-seqs` 16, `max-model-len` 4096 으로 축소

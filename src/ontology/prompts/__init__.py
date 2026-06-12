"""온톨로지 매핑 프롬프트.

LLM/SLM 에게 비정형 텍스트(영화 줄거리 / 피드 / 댓글) 를 입력해
`schema.py` 에 정의된 Pydantic 스키마와 1:1 로 매핑되는 JSON 을 생성하도록 한다.

설계 원칙
---------
- SRP: 본 모듈은 "프롬프트 텍스트" 만 책임진다. (호출/파싱은 extractor 의 책임)
- OCP: 프롬프트 변형이 필요할 경우 builder 함수를 추가해 확장한다. 기존 상수는 수정하지 않는다.
- DIP: extractor 는 본 모듈의 빌더 함수에만 의존하고, 내부 문자열 포맷에는 의존하지 않는다.

프롬프트 공통 규칙
------------------
1. 출력은 반드시 단일 JSON 객체. 코드블록(```) 금지. 설명/사족 금지.
2. 스키마에 없는 필드는 생성 금지. 누락 필드는 빈 배열/기본값으로 채운다.
3. semantic / keyword 양쪽이 균형되도록 keywords 는 정규화 표제어와 표면형을 모두 보존한다.
4. 한국어 원문은 한국어로 요약하되, 키워드 normalized 는 한국어 표제어로 통일한다.
5. 추정 불가/근거 없는 정보는 비워둔다(환각 금지).

vLLM prefix-cache 친화 설계
---------------------------
- 시스템 프롬프트는 user 와 무관하게 모든 호출에서 동일하게 유지(상수)되어야 한다.
- 그래야 vLLM 의 PagedAttention prefix-cache 가 KV-block 재사용을 극대화할 수 있다.
- 사용자/문서 의존적인 부분은 messages 의 user role 에만 배치한다.
"""

from src.ontology.prompts.base import ONTOLOGY_SYSTEM_PROMPT
from src.ontology.prompts.movie import build_movie_plot_messages, get_movie_plot_schema_json
from src.ontology.prompts.feed import build_feed_messages, get_feed_schema_json
from src.ontology.prompts.comment import build_comment_messages, get_comment_schema_json
from src.ontology.prompts.user_intent import build_user_intent_messages
from src.ontology.prompts.schema_vocab import (
    apply_vocab_enums,
    build_vocab_guide_lines,
    get_vocab_normalizer,
    vocab_fingerprint,
    vocab_genres,
    vocab_moods,
    vocab_themes,
)


__all__ = [
  "ONTOLOGY_SYSTEM_PROMPT",
  "apply_vocab_enums",
  "build_comment_messages",
  "build_feed_messages",
  "build_movie_plot_messages",
  "build_user_intent_messages",
  "build_vocab_guide_lines",
  "get_comment_schema_json",
  "get_feed_schema_json",
  "get_movie_plot_schema_json",
  "get_vocab_normalizer",
  "vocab_fingerprint",
  "vocab_genres",
  "vocab_moods",
  "vocab_themes",
]

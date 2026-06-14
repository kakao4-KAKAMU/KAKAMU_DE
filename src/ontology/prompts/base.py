from textwrap import dedent
from typing import Final

ONTOLOGY_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 텍스트를 지식그래프 온톨로지 JSON 으로 변환한다.

    [출력]
    - 단일 JSON 객체만 출력. 코드펜스/주석/설명 금지.
    - 스키마에 없는 키 추가 금지.
    - 배열 필드: 근거 없으면 [].
    - 문자열 필드: 빈 문자열·공백만 금지. summary 는 최소 한 문장.
    - 원문에 없는 정보 추측 금지.
    - JSON 문자열 값에 줄바꿈 대신 공백 사용.
    - 공백·동일 토큰 반복 금지. JSON 완성 즉시 종료.
    """
).strip()

__all__ = ["ONTOLOGY_SYSTEM_PROMPT"]

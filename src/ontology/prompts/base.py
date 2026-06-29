from textwrap import dedent
from typing import Final

ONTOLOGY_SYSTEM_PROMPT: Final[str] = dedent(
    """
    너는 텍스트를 지식그래프 온톨로지 JSON 으로 변환한다.

    [출력]
    - 배열 필드: 근거 없으면 [].
    - 문자열 필드: 빈 문자열·공백만 금지. summary 는 최소 한 문장.
    - 원문에 없는 정보 추측 금지.
    """
).strip()

__all__ = ["ONTOLOGY_SYSTEM_PROMPT"]

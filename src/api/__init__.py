"""FastAPI 진입점.

``from src.api import create_app`` 으로 app 인스턴스를 얻을 수 있다.
"""

from src.api.app import create_app

__all__ = ["create_app"]

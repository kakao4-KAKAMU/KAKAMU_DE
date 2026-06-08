# Python 패키지 전용 베이스 이미지 (requirements.txt).
# torch / sentence-transformers 등 GPU·로컬 ML 스택은 포함하지 않습니다.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt pyproject.toml ./

RUN pip install -r requirements.txt \
    && find /usr/local/lib/python3.12/site-packages -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /usr/local/lib/python3.12/site-packages -type d \( -name tests -o -name test \) -prune -exec rm -rf {} + \
    && rm -rf /root/.cache

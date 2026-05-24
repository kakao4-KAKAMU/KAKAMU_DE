FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# psycopg / neo4j 등 네이티브 빌드 의존성 (slim 이미지)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

EXPOSE 8080

# 기본: FastAPI. worker/bootstrap 는 docker-compose 에서 command override.
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]

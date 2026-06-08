ARG BASE_IMAGE=movie-recommend-system-base:latest
FROM ${BASE_IMAGE}

ENV PYTHONPATH=/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=8 \
    CMD curl -f http://localhost:8080/healthz || exit 1

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]

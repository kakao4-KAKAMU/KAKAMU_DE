ARG BASE_IMAGE=movie-recommend-system-base:latest
FROM ${BASE_IMAGE}

ENV PYTHONPATH=/app

WORKDIR /app

COPY . .

CMD ["python", "scripts/run_ingest_worker.py", "--concurrency", "10"]

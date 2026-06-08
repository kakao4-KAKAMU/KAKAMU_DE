ARG BASE_IMAGE=movie-recommend-system-base:latest
FROM ${BASE_IMAGE}

ENV PYTHONPATH=/app

WORKDIR /app

COPY . .

EXPOSE 8080

CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8080"]

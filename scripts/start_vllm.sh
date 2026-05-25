#!/usr/bin/env bash
# Tesla T4 16GB: generation (0.65) + embedding (0.20) on single GPU.
# Requires: pip install vllm, CUDA 12.1+, driver 535+

set -euo pipefail

GEN_MODEL="${VLLM_GEN_MODEL:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
EMBED_MODEL="${VLLM_EMBED_MODEL:-BAAI/bge-m3}"
GEN_PORT="${VLLM_GEN_PORT:-8000}"
EMBED_PORT="${VLLM_EMBED_PORT:-8001}"

echo "Starting vLLM generation on :${GEN_PORT} (${GEN_MODEL})"
python -m vllm.entrypoints.openai.api_server \
  --model "${GEN_MODEL}" \
  --port "${GEN_PORT}" \
  --dtype auto \
  --quantization awq \
  --gpu-memory-utilization 0.65 \
  --max-model-len 8192 \
  --max-num-seqs 32 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --block-size 16 \
  &
GEN_PID=$!

echo "Starting vLLM embedding on :${EMBED_PORT} (${EMBED_MODEL})"
python -m vllm.entrypoints.openai.api_server \
  --model "${EMBED_MODEL}" \
  --port "${EMBED_PORT}" \
  --runner pooling \
  --gpu-memory-utilization 0.20 \
  --hf-overrides '{"architectures": ["BgeM3EmbeddingModel"]}' \
  &
EMBED_PID=$!

trap 'kill ${GEN_PID} ${EMBED_PID} 2>/dev/null || true' EXIT

echo "Generation PID=${GEN_PID}, Embedding PID=${EMBED_PID}"
wait

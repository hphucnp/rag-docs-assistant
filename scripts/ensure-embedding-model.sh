#!/usr/bin/env sh
set -eu

EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-ollama}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

echo "[ensure-embedding-model] Checking embedding provider: ${EMBEDDING_PROVIDER}"

# Only Ollama requires model pulling (OpenAI/Cohere are cloud services)
if [ "$EMBEDDING_PROVIDER" != "ollama" ]; then
  echo "[ensure-embedding-model] Using ${EMBEDDING_PROVIDER} (no local model needed)."
  exit 0
fi

echo "[ensure-embedding-model] Checking if Ollama model '${EMBEDDING_MODEL}' exists..."

# Check if model already exists in Ollama
OLLAMA_HOST="${OLLAMA_BASE_URL#http://}"
OLLAMA_HOST="${OLLAMA_HOST#https://}"

if ollama list 2>/dev/null | grep -q "$EMBEDDING_MODEL"; then
  echo "[ensure-embedding-model] Model '${EMBEDDING_MODEL}' already exists."
  exit 0
fi

echo "[ensure-embedding-model] Model '${EMBEDDING_MODEL}' not found. Pulling..."

if ! ollama pull "$EMBEDDING_MODEL"; then
  echo "[ensure-embedding-model] Failed to pull model '${EMBEDDING_MODEL}'."
  exit 1
fi

echo "[ensure-embedding-model] Successfully pulled model '${EMBEDDING_MODEL}'."
exit 0

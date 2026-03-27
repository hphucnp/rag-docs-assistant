#!/usr/bin/env sh
set -eu

EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

echo "[ollama-entrypoint] Starting Ollama server in background..."
# Start the Ollama server in background
/bin/ollama serve &
OLLAMA_PID=$!

echo "[ollama-entrypoint] Waiting for Ollama server to be ready..."
# Wait for Ollama to be ready
for i in $(seq 1 30); do
  if ollama list >/dev/null 2>&1; then
    echo "[ollama-entrypoint] Ollama server is ready"
    break
  fi
  echo "[ollama-entrypoint] Waiting... (attempt $i/30)"
  sleep 1
done

echo "[ollama-entrypoint] Pulling model: ${EMBEDDING_MODEL}"
if ollama pull "$EMBEDDING_MODEL"; then
  echo "[ollama-entrypoint] Successfully pulled model '${EMBEDDING_MODEL}'"
else
  echo "[ollama-entrypoint] Failed to pull model '${EMBEDDING_MODEL}', but continuing..."
fi

echo "[ollama-entrypoint] Ollama ready with model '${EMBEDDING_MODEL}'"

# Keep the server running
wait $OLLAMA_PID

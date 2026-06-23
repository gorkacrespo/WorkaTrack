#!/bin/sh
set -eu

ollama serve &
pid=$!

cleanup() {
  kill "$pid" 2>/dev/null || true
}
trap cleanup INT TERM

echo "[ollama] esperando a que el servidor esté disponible..."
for _ in $(seq 1 60); do
  if ollama list >/dev/null 2>&1; then
    echo "[ollama] servidor disponible"
    break
  fi
  sleep 2
done

echo "[ollama] asegurando modelo base qwen2.5:3b..."
ollama pull qwen2.5:3b

echo "[ollama] asegurando modelo de embeddings nomic-embed-text..."
ollama pull nomic-embed-text

echo "[ollama] construyendo modelo portable workatrack-qa-fast:latest..."
ollama create workatrack-qa-fast:latest -f /models/Modelfile.workatrack-qa-fast.compose

echo "[ollama] inicialización completada"
wait "$pid"

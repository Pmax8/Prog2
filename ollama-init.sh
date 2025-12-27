#!/bin/sh
set -e

echo "[ollama] avvio ollama..."
ollama serve &
PID=$!

echo "[ollama] aspetto che ollama risponda..."
until wget -qO- http://localhost:11434/api/tags >/dev/null 2>&1; do
  sleep 1
done

MODEL1="gemma3:1b-it-qat"
MODEL2="gemma3:1b-it-q4_K_M"

echo "[ollama] scarico il modello: $MODEL1"
ollama pull "$MODEL1" || true

echo "[ollama] scarico il modello: $MODEL2"
ollama pull "$MODEL2" || true

echo "[ollama] pronto"
wait $PID

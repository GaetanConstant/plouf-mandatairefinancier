#!/bin/bash

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Démarrage du backend..."
cd "$ROOT/backend"
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Démarrage du frontend..."
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

cleanup() {
  echo "Arrêt de l'application..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

echo "Application lancée. Ctrl+C pour arrêter."
wait

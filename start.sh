#!/bin/bash
# Lance l'application en développement.
#
# Les ports sont propres à ce projet : 8000 et 5173 sont les défauts de tout le
# monde, et un autre projet qui tourne déjà les occupe. Quand cela arrive, le
# backend n'arrive pas à démarrer pendant que Vite bascule silencieusement sur
# un autre port — le navigateur finit par parler à l'API du voisin, et la
# connexion échoue sans rien expliquer.
#
# Surchargeables : PORT_API=8001 PORT_WEB=5174 ./start.sh

set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT_API="${PORT_API:-8001}"
PORT_WEB="${PORT_WEB:-5174}"
API_URL="http://localhost:${PORT_API}"
WEB_URL="http://localhost:${PORT_WEB}"

occupe() {
  lsof -i ":$1" -sTCP:LISTEN -t >/dev/null 2>&1
}

decrire_occupant() {
  local pid
  pid=$(lsof -i ":$1" -sTCP:LISTEN -t 2>/dev/null | head -1)
  [ -n "$pid" ] && ps -p "$pid" -o command= 2>/dev/null | cut -c1-90
}

for couple in "API:$PORT_API" "WEB:$PORT_WEB"; do
  role="${couple%%:*}"; port="${couple##*:}"
  if occupe "$port"; then
    echo "Port $port ($role) déjà utilisé par :"
    echo "   $(decrire_occupant "$port")"
    echo "Arrêtez ce processus, ou relancez avec d'autres ports :"
    echo "   PORT_API=8002 PORT_WEB=5175 ./start.sh"
    exit 1
  fi
done

echo "Démarrage du backend sur $API_URL ..."
cd "$ROOT/backend"
# Le front est servi depuis PORT_WEB : sans cette origine, le navigateur bloque
# la réponse du login et l'écran n'affiche qu'une « erreur de connexion ».
CORS_ORIGINS="$WEB_URL" uv run uvicorn main:app --host 127.0.0.1 --port "$PORT_API" --reload &
BACKEND_PID=$!

echo "Démarrage du frontend sur $WEB_URL ..."
cd "$ROOT/frontend"
# --strictPort : mieux vaut un échec net qu'une bascule silencieuse vers un
# port dont le backend ignore tout.
VITE_API_URL="$API_URL" npm run dev -- --port "$PORT_WEB" --strictPort &
FRONTEND_PID=$!

cleanup() {
  echo "Arrêt de l'application..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

echo ""
echo "Application lancée : $WEB_URL"
echo "Ctrl+C pour arrêter."
wait

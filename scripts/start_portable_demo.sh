#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "[demo] levantando stack portable..."
docker compose -f docker-compose.portable.yml up -d --build db ollama web frontend

echo "[demo] sembrando escenarios demo..."
docker compose -f docker-compose.portable.yml run --rm --entrypoint python web -m app.scripts.seed_portable_demo_large

echo "[demo] listo"
echo "URL: http://localhost:3000"
echo "Usuario: demo"
echo "Password: demo1234"
echo "Password del proyecto: proyecto1234"

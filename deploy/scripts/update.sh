#!/bin/bash
# NetSync Gov — Mise à jour sans downtime
set -euo pipefail

DEPLOY_DIR="/opt/netsync_gov"
cd $DEPLOY_DIR

echo "[1/4] Pull dernières modifications..."
git pull origin main

echo "[2/4] Build nouvelles images..."
docker compose -f deploy/docker-compose.prod.yml build --no-cache api worker beat frontend

echo "[3/4] Migrations Alembic..."
docker compose -f deploy/docker-compose.prod.yml run --rm api alembic upgrade head

echo "[4/4] Redémarrage rolling..."
docker compose -f deploy/docker-compose.prod.yml up -d --no-deps api worker beat frontend

echo "=== Mise à jour terminée ==="
docker compose -f deploy/docker-compose.prod.yml ps

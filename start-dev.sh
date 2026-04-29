#!/bin/bash
echo "🚀 NetSync Gov — Démarrage complet..."
cd ~/appels-offres-bf
source .env 2>/dev/null
export DATABASE_URL=${DATABASE_URL:-postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev}
export PDF_STORAGE_DIR=${PDF_STORAGE_DIR:-backend/static/pdfs}
mkdir -p backend/static/pdfs

# DB + Redis
docker compose -f deploy/docker-compose.dev.yml up -d db redis
sleep 6
docker exec netsync_db_dev pg_isready -U netsync && echo "✅ DB" || echo "❌ DB"

# Backend
pkill -f uvicorn 2>/dev/null; sleep 1
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
sleep 3

# Frontend
pkill -f vite 2>/dev/null; sleep 1
cd frontend && npm run dev -- --host 0.0.0.0 --port 5173 &
cd ..
sleep 3

echo ""
echo "════════════════════════════════════════"
echo "✅ NetSync Gov prêt !"
echo "   Frontend : http://localhost:5173"
echo "   Backend  : http://localhost:8000"
echo "   Swagger  : http://localhost:8000/docs"
echo "   Health   : http://localhost:8000/health/detailed"
echo "════════════════════════════════════════"

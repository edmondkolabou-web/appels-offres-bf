#!/bin/bash
echo "🚀 Démarrage NetSync Gov..."
cd ~/appels-offres-bf

# 1. DB + Redis
docker compose -f deploy/docker-compose.dev.yml up -d db redis
sleep 5
docker exec netsync_db_dev pg_isready -U netsync && echo "✅ DB" || echo "❌ DB"

# 2. Backend
pkill -f uvicorn 2>/dev/null; sleep 1
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
sleep 3

# 3. Frontend
pkill -f vite 2>/dev/null; sleep 1
cd frontend && npm run dev -- --host 0.0.0.0 --port 5173 &
cd ..
sleep 3

echo ""
echo "✅ Tout est lancé :"
echo "   Frontend : http://localhost:5173"
echo "   Backend  : http://localhost:8000/docs"
echo "   Health   : http://localhost:8000/health/detailed"

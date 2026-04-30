#!/bin/bash
echo "🚀 Pipeline NetSync Gov..."
cd ~/appels-offres-bf
source .env 2>/dev/null
export DATABASE_URL=${DATABASE_URL:-postgresql://netsync:devpassword@localhost:5432/netsync_gov_dev}
export PDF_STORAGE_DIR=${PDF_STORAGE_DIR:-backend/static/pdfs}
mkdir -p backend/static/pdfs

# DB
docker compose -f deploy/docker-compose.dev.yml up -d db redis
sleep 8
docker exec netsync_db_dev pg_isready -U netsync || { echo "❌ DB pas prête"; exit 1; }
echo "✅ DB prête"

# Pipeline
python3 -c "
import os
from pipeline.pipeline import PipelineOrchestrator, get_db
import logging; logging.basicConfig(level=logging.INFO)
db=get_db(); p=PipelineOrchestrator(db); r=p.run()
print(f'PDFs:{r[\"pdfs_traites\"]} AOs:{r[\"ao_extraits\"]} Insérés:{r[\"ao_inseres\"]}')
if r['erreurs']:
    for e in r['erreurs'][:3]: print(f'  ⚠️ {e[:150]}')
else:
    print('✅ Pipeline terminé avec succès')
db.close()
"

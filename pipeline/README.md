# NetSync Gov — Pipeline PDF DGCMEF

Agrégateur automatique des Appels d'Offres publiés par la DGCMEF Burkina Faso.

## Architecture

```
pipeline.py          # Orchestrateur — coordonne les 6 étapes
├── watcher.py       # Étape 1 : Scrape DGCMEF + télécharge PDFs
├── parser.py        # Étape 2-3 : Extraction texte + parsing AOs
├── normalizer.py    # Étape 4-5 : Normalisation + insertion PostgreSQL
└── alerts.py        # Étape 6 : Email (Resend) + WhatsApp (Meta API)

models.py            # Modèles SQLAlchemy — 7 tables
config.py            # Configuration centralisée (env vars)
requirements.txt     # Dépendances Python
docker-compose.yml   # Stack complète (PostgreSQL, Redis, Celery)
```

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env  # Configurer les variables
python pipeline.py    # Test en mode direct
```

## Variables d'environnement

```env
DATABASE_URL=postgresql://netsync:pass@localhost:5432/netsync_gov
REDIS_URL=redis://localhost:6379/0
RESEND_API_KEY=re_xxx
WHATSAPP_API_TOKEN=xxx
WHATSAPP_PHONE_ID=xxx
ANTHROPIC_API_KEY=sk-ant-xxx
PDF_STORAGE_DIR=/data/pdfs
```

## Lancement en production

```bash
# Initialiser les migrations
alembic upgrade head

# Démarrer avec Docker
docker-compose up -d

# Ou manuellement
celery -A pipeline.celery_app worker --loglevel=info &
celery -A pipeline.celery_app beat --loglevel=info &
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Pipeline quotidien (07h00, Lun-Ven)

1. **Watcher** — Scrape dgcmef.gov.bf, détecte nouveaux numéros, télécharge PDFs
2. **Extraction** — pdfplumber extrait texte brut page par page
3. **Parsing** — Regex + heuristiques identifient les champs de chaque AO
4. **Normalisation** — Nettoyage, validation, déduplication par référence
5. **Insertion** — PostgreSQL upsert + mise à jour search_vector (GIN)
6. **Alertes** — Email (Resend) + WhatsApp (Meta API) aux abonnés Pro

## Moat technique

Le pipeline est la barrière défensive du produit :
- Parsing PDF robuste qui gère les variations de mise en page du Quotidien
- Fallback LLM (Claude) pour les cas ambigus (confiance < 0.4)
- Déduplication par référence officielle + référence synthétique
- Index GIN pour matching secteur en O(log n) sur ARRAY PostgreSQL

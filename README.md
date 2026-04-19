# NetSync Gov — Appels d'offres publics Burkina Faso

**gov.netsync.bf** · Premier agrégateur burkinabè d'appels d'offres avec alertes WhatsApp automatiques.

## Structure du projet

```
NetSync_Gov_COMPLET/
├── backend/              # API FastAPI + modules gestion marchés
│   ├── main.py           # Point d'entrée FastAPI
│   ├── database.py       # SQLAlchemy + PostgreSQL
│   ├── security.py       # JWT + guards
│   ├── schemas.py        # Modèles Pydantic
│   ├── routers/          # 6 routers : auth, aos, alertes, favoris, paiements, admin
│   ├── alertes/          # Resend email + WhatsApp Meta API
│   ├── paiement/         # CinetPay Orange Money / Moov
│   └── modules/          # 5 modules Gestion des marchés publics
│       ├── candidature/  # Dossier soumission assisté IA
│       ├── intelligence/ # Analyses et tendances
│       ├── conformite/   # Coffre-fort administratif
│       ├── transparence/ # Open Data + parser attributions
│       └── institutions/ # Plateforme acheteur public (B2G)
├── frontend/             # Vue.js 3 + Vite + Pinia
│   └── src/
│       ├── views/        # 12 vues (+ 4 modules)
│       ├── stores/       # Pinia stores
│       ├── components/   # Composants réutilisables
│       └── assets/       # Design system CSS
├── pipeline/             # Pipeline PDF DGCMEF (6 étapes)
│   ├── watcher.py        # Détection nouveaux PDFs
│   ├── parser.py         # Extraction texte pdfplumber
│   ├── normalizer.py     # Normalisation données
│   ├── models.py         # Modèles BDD
│   ├── pipeline.py       # Orchestration Celery
│   └── alerts.py         # Dispatch alertes
├── deploy/               # Infrastructure production
│   ├── docker-compose.prod.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── scripts/          # deploy.sh, update.sh, init.sql
│   ├── nginx/            # Configuration Nginx + SSL
│   └── monitoring/       # Healthcheck
├── tests/                # 96 tests pytest
│   ├── modules/          # Tests par module
│   ├── integration/      # Tests API + pipeline
│   └── security/         # Audit sécurité
├── docs/                 # Documentation complète
│   ├── modules/          # Analyses besoin par module
│   ├── analyses/         # Business plan, GTM, roadmap
│   └── guides/           # Guide déploiement 6 étapes
└── assets/               # Logo + maquettes HTML

```

## Stack technique

| Couche | Technologie |
|--------|------------|
| Backend | FastAPI Python 3.11 + PostgreSQL 15 + Redis 7 + Celery |
| Frontend | Vue.js 3 + Vite + Pinia |
| Parsing PDF | pdfplumber + regex + Claude API |
| Email | Resend |
| WhatsApp | Meta Cloud API v18 |
| Paiement | CinetPay (Orange Money, Moov Money) |
| Deploy | Docker Compose + Nginx + Let's Encrypt |
| Hébergement | VPS Hostinger KVM 2 |

## Démarrage rapide

```bash
# 1. Copier et remplir le fichier d'environnement
cp docs/guides/env_production_template.txt deploy/.env.production
nano deploy/.env.production

# 2. Lancer le déploiement
chmod +x deploy/scripts/deploy.sh
./deploy/scripts/deploy.sh

# 3. Lancer les tests
python -m pytest tests/ -v
```

## Chiffres clés

- **118+ fichiers** · **12 000+ lignes de code** · **96 tests pytest**
- **Break-even** : 5 abonnés Pro (75 000 FCFA/mois)
- **MRR cible M12** : 5 800 000 FCFA

## Plans tarifaires

| Plan | Prix mensuel |
|------|-------------|
| Gratuit | 0 FCFA |
| Pro | 15 000 FCFA |
| Équipe | 45 000 FCFA |
| Institutionnel | 75 000 FCFA |

---
Un produit **NetSync Africa** · contact@netsync.bf · gov.netsync.bf

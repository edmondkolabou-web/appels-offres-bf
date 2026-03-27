# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

**Appels Offres BF** — Plateforme d'agrégation et de diffusion des appels d'offres publics et privés du Burkina Faso.

## Stack technique

- **Python 3.10** + virtualenv (`source venv/bin/activate`)
- **SQLite** — base de données locale (`database/appels_offres.db`)
- **FastAPI + Uvicorn** — API REST et serveur web
- **BeautifulSoup4 + Requests** — scraping des sources
- **Pydantic v2** — validation des données

## Sources scrapées

| Source | URL | Type |
|--------|-----|------|
| Journal des Offres | joffres.net | Public |
| Les Affaires BF | lesaffairesbf.com | Public/Privé |
| CCI Burkina Faso | cci.bf | Privé |

## Fonctionnalités

- Scraping automatique des trois sources
- Alertes email et SMS (mots-clés, secteur, montant)
- Espace entreprise (profil, abonnement, favoris)
- Tableau de bord statistiques

## Structure

```
database/database.py   — modèles SQLite (offres, utilisateurs, alertes, favoris)
scraper/scraper.py     — orchestrateur de scraping
scraper/sources.py     — scrapers par source (joffres, lesaffaires, cci)
api/main.py            — routes FastAPI
templates/index.html   — interface web
requirements.txt       — dépendances Python
```

## Commandes

```bash
source venv/bin/activate
python database/database.py        # initialiser/vérifier la BDD
uvicorn api.main:app --reload      # lancer le serveur de dev
python scraper/scraper.py          # lancer un scraping manuel
```

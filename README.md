# 🇧🇫 Appels Offres BF

Plateforme d'agrégation et de diffusion des appels d'offres publics et privés du Burkina Faso.

Scrape automatiquement les sources officielles, expose une API REST et une interface web, et envoie des alertes email personnalisées aux utilisateurs abonnés.

---

## Fonctionnalités

- **Scraping automatique** de [lesaffairesbf.com](https://www.lesaffairesbf.com) et [arcop.bf](https://www.arcop.bf)
- **API REST** (FastAPI) : liste, recherche, filtres, statistiques
- **Interface web** responsive consommant l'API
- **Alertes email** : matching par mots-clés, secteur et type d'offre
- **Base SQLite** : offres, utilisateurs, alertes, favoris

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.10+ |
| API | FastAPI + Uvicorn |
| Base de données | SQLite |
| Scraping | Requests + BeautifulSoup4 |
| Email | smtplib (stdlib Python) |
| Frontend | HTML/CSS/JS vanilla |

---

## Installation locale

### Prérequis

- Python 3.10 ou supérieur
- pip

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/votre-compte/appels-offres-bf.git
cd appels-offres-bf

# 2. Créer et activer le virtualenv
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les variables d'environnement (optionnel — pour les alertes email)
cp .env.example .env
# Éditer .env avec vos identifiants SMTP

# 5. Initialiser la base de données
python database/database.py

# 6. Lancer un premier scraping
python scraper/scraper.py

# 7. Démarrer le serveur
uvicorn api.main:app --reload
```

L'interface web est disponible sur **http://127.0.0.1:8000**

---

## Structure du projet

```
appels-offres-bf/
├── api/
│   └── main.py              # Routes FastAPI
├── alertes/
│   └── alertes.py           # Système d'alertes email
├── database/
│   ├── database.py          # Schéma SQLite + helpers
│   └── appels_offres.db     # Base de données (générée)
├── scraper/
│   ├── scraper.py           # Orchestrateur de scraping
│   └── sources.py           # Scrapers par source
├── templates/
│   └── index.html           # Interface web
├── .env.example             # Variables d'environnement à configurer
├── Procfile                 # Point d'entrée Render.com
└── requirements.txt         # Dépendances Python
```

---

## Routes API

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/` | Interface web |
| `GET` | `/api` | Informations API (JSON) |
| `GET` | `/offres` | Liste paginée (`?page=1&limite=10&source=arcop&statut=ouvert`) |
| `GET` | `/offres/{id}` | Détail d'une offre |
| `GET` | `/offres/search` | Recherche par mot-clé (`?q=construction`) |
| `GET` | `/stats` | Statistiques : total, par source, dernière MàJ |
| `GET` | `/alertes/test` | Email de test (`?email=vous@example.com`) |
| `POST` | `/alertes/run` | Déclenche le traitement des alertes |

Documentation interactive : **http://127.0.0.1:8000/docs**

---

## Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `SMTP_HOST` | `smtp.gmail.com` | Serveur SMTP |
| `SMTP_PORT` | `587` | Port SMTP (TLS) |
| `SMTP_USER` | — | Adresse email expéditeur |
| `SMTP_PASS` | — | Mot de passe SMTP (ou mot de passe d'application) |
| `PORT` | `8000` | Port serveur (défini automatiquement par Render) |

Sans `SMTP_USER` et `SMTP_PASS`, les emails sont simulés (affichage console) sans erreur.

---

## Déploiement sur Render.com

### Étapes

1. **Pousser le code sur GitHub** (dépôt public ou privé)

2. **Créer un compte** sur [render.com](https://render.com)

3. **Nouveau Web Service** → connecter le dépôt GitHub

4. **Configurer le service** :

   | Champ | Valeur |
   |-------|--------|
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |

   *(Render détecte automatiquement le `Procfile`)*

5. **Variables d'environnement** → ajouter dans l'onglet "Environment" :
   ```
   SMTP_HOST     smtp.gmail.com
   SMTP_PORT     587
   SMTP_USER     votre@email.com
   SMTP_PASS     votre_mot_de_passe_app
   ```

6. **Déployer** — Render installe les dépendances et démarre le serveur.

### Note sur la base de données

Render utilise un **système de fichiers éphémère** : la base SQLite est remise à zéro à chaque redéploiement. Pour une utilisation en production :

- Utiliser **Render PostgreSQL** (gratuit jusqu'à 1 Go) en remplaçant SQLite par `psycopg2`
- Ou exporter/importer la base via un volume persistant (plan payant)

Pour un usage démonstration ou MVP, SQLite suffit.

---

## Sources de données

| Source | Type | URL |
|--------|------|-----|
| Les Affaires BF | Marchés publics (agrégateur) | lesaffairesbf.com |
| ARCOP | Autorité de Régulation de la Commande Publique | arcop.bf |

---

## Licence

MIT

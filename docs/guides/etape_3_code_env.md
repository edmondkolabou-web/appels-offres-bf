# Étape 3 — Mettre le code sur le VPS et remplir .env.production

> Prérequis : étape 2 terminée, tu as accès au VPS par SSH.
> Durée : 20 à 30 minutes.

---

## 3a — Créer le dépôt GitHub

Si ce n'est pas encore fait, mettre le code dans un repo GitHub privé.

### Sur ton ordinateur
```bash
# Aller dans le dossier NetSync_Gov (le ZIP décompressé)
cd /chemin/vers/NetSync_Gov

# Initialiser Git
git init
git add .
git commit -m "Initial commit — NetSync Gov v1.0"

# Créer un repo sur github.com (bouton + → New repository)
# Nom : appels-offres-bf
# Visibilité : Private

# Lier et pousser
git remote add origin https://github.com/TON_USERNAME/appels-offres-bf.git
git branch -M main
git push -u origin main
```

---

## 3b — Cloner le code sur le VPS

```bash
# Se connecter au VPS
ssh root@185.XXX.XXX.XXX

# Créer le dossier de travail
mkdir -p /opt/netsync_gov
cd /opt/netsync_gov

# Cloner le repo
git clone https://github.com/TON_USERNAME/appels-offres-bf.git .

# Vérifier que les fichiers sont là
ls -la
# Tu dois voir : 01_Analyse_Marche/ 02_Strategie_Produit/ ... 18_Guide_Deploiement_Pas_a_Pas/ etc.
```

---

## 3c — Remplir le fichier .env.production

C'est l'étape la plus importante. Ce fichier contient TOUTES les clés.

```bash
# Sur le VPS, aller dans le dossier déploiement
cd /opt/netsync_gov/13_Deploiement_Docker_VPS

# Copier le template
cp .env.production .env.production.rempli

# Ouvrir l'éditeur
nano .env.production.rempli
```

### Contenu complet à remplir

```bash
# ── Base de données ──────────────────────────────────────────────────────────
# Inventer un mot de passe fort (ex: générer sur https://passwordsgenerator.net)
DB_PASSWORD=INVENTER_UN_MOT_DE_PASSE_FORT_ICI

# ── Redis ────────────────────────────────────────────────────────────────────
# Autre mot de passe fort (différent du DB)
REDIS_PASSWORD=AUTRE_MOT_DE_PASSE_FORT_ICI

# ── JWT ──────────────────────────────────────────────────────────────────────
# Générer une chaîne aléatoire de 64+ caractères :
# Sur le VPS : python3 -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=COLLER_ICI_LA_CHAINE_GENEREE

# ── Resend (email) ───────────────────────────────────────────────────────────
# Récupéré à l'étape 1 - Compte Resend
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=alertes@gov.netsync.bf
RESEND_REPLY_TO=support@netsync.bf

# ── WhatsApp Business API (Meta) ─────────────────────────────────────────────
# Récupéré à l'étape 1 - Compte Meta
WHATSAPP_API_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_ID=1234567890123
WHATSAPP_WABA_ID=9876543210987

# ── Claude API (parsing fallback) ────────────────────────────────────────────
# Récupéré à l'étape 1 - Compte Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ── CinetPay ─────────────────────────────────────────────────────────────────
# Récupéré à l'étape 1 - Compte CinetPay
CINETPAY_SITE_ID=xxxxxxxxx
CINETPAY_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
CINETPAY_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxx
CINETPAY_NOTIFY_URL=https://api.gov.netsync.bf/api/v1/paiements/webhook
CINETPAY_RETURN_URL=https://gov.netsync.bf/paiement/succes

# ── Admin ─────────────────────────────────────────────────────────────────────
ADMIN_EMAIL=ton.email@gmail.com
ADMIN_EMAILS=ton.email@gmail.com

# ── Domaines ──────────────────────────────────────────────────────────────────
DOMAIN=gov.netsync.bf
API_DOMAIN=api.gov.netsync.bf
ENVIRONMENT=production
```

### Générer le JWT_SECRET_KEY
```bash
# Sur le VPS, lancer cette commande et copier le résultat
python3 -c "import secrets; print(secrets.token_hex(32))"
# Exemple de résultat : a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1
```

### Sauvegarder
```bash
# Dans nano : Ctrl+X → Y → Entrée

# Copier vers le nom attendu par docker-compose
cp .env.production.rempli .env.production

# IMPORTANT : vérifier que le fichier est bien rempli
grep "CHANGE_ME\|xxxxxxx\|INVENTER" .env.production
# Cette commande NE doit rien afficher si tout est bien rempli
```

---

## 3d — Vérification finale étape 3

```bash
# Sur le VPS
cd /opt/netsync_gov/13_Deploiement_Docker_VPS

# Vérifier que .env.production existe et n'a pas de valeurs vides
cat .env.production | grep -v "^#" | grep -v "^$"
# Toutes les lignes doivent avoir une valeur après le =

# Vérifier que .gitignore protège le fichier .env
cd /opt/netsync_gov
cat .gitignore | grep ".env"
# Doit afficher : .env*
```

**Si tout est bon → passer à l'étape 4.**

> SÉCURITÉ : Ne jamais partager le contenu de .env.production.
> Ne jamais le committer sur GitHub (le .gitignore l'en empêche).

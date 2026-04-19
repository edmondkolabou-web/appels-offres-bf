#!/bin/bash
# NetSync Gov — Script de déploiement initial sur VPS Hostinger
# Usage : ./scripts/deploy.sh
set -euo pipefail

DOMAIN="gov.netsync.bf"
REPO="https://github.com/VOTRE_USERNAME/appels-offres-bf.git"
DEPLOY_DIR="/opt/netsync_gov"
EMAIL_CERTBOT="admin@netsync.bf"

echo "=== NetSync Gov — Déploiement ==="
echo "Domaine : $DOMAIN"
echo ""

# ── 1. Prérequis ──────────────────────────────────────────────────────────────
echo "[1/8] Installation des prérequis..."
apt-get update -qq
apt-get install -y -qq docker.io docker-compose-plugin git curl ufw

# Docker au démarrage
systemctl enable docker
systemctl start docker

# ── 2. Firewall ───────────────────────────────────────────────────────────────
echo "[2/8] Configuration firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

# ── 3. Code source ────────────────────────────────────────────────────────────
echo "[3/8] Clonage du dépôt..."
mkdir -p $DEPLOY_DIR
cd $DEPLOY_DIR

if [ -d ".git" ]; then
    git pull origin main
else
    git clone $REPO .
fi

# ── 4. Variables d'environnement ──────────────────────────────────────────────
echo "[4/8] Configuration des variables d'environnement..."
if [ ! -f "deploy/.env.production" ]; then
    cp deploy/.env.production.example deploy/.env.production
    echo "ATTENTION : édite deploy/.env.production avant de continuer !"
    echo "Appuie sur Entrée quand c'est fait..."
    read -r
fi

# Copier .env pour docker-compose
cp deploy/.env.production .env

# ── 5. Migrations Alembic ─────────────────────────────────────────────────────
echo "[5/8] Migrations base de données..."
docker compose -f deploy/docker-compose.prod.yml up -d db redis
sleep 10  # Attendre que PostgreSQL soit prêt

docker compose -f deploy/docker-compose.prod.yml run --rm api \
    alembic upgrade head

# ── 6. SSL Let's Encrypt ──────────────────────────────────────────────────────
echo "[6/8] Certificat SSL..."
docker compose -f deploy/docker-compose.prod.yml up -d nginx

# Obtenir le certificat (mode staging pour tester)
docker run --rm \
    -v "$(pwd)/ssl_certs:/etc/letsencrypt" \
    -v "$(pwd)/ssl_www:/var/www/certbot" \
    certbot/certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    --email $EMAIL_CERTBOT \
    --agree-tos --no-eff-email \
    -d $DOMAIN -d api.$DOMAIN

# ── 7. Démarrage complet ──────────────────────────────────────────────────────
echo "[7/8] Démarrage de tous les services..."
docker compose -f deploy/docker-compose.prod.yml up -d

# ── 8. Vérification ───────────────────────────────────────────────────────────
echo "[8/8] Vérification..."
sleep 15

if curl -sf "https://$DOMAIN" > /dev/null; then
    echo "✓ Frontend accessible"
else
    echo "✗ Frontend non accessible"
fi

if curl -sf "https://api.$DOMAIN/health" > /dev/null; then
    echo "✓ API accessible"
else
    echo "✗ API non accessible"
fi

echo ""
echo "=== Déploiement terminé ==="
echo "Frontend : https://$DOMAIN"
echo "API :      https://api.$DOMAIN"
echo "Docs :     https://api.$DOMAIN/docs"

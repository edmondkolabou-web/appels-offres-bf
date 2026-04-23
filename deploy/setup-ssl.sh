#!/bin/bash
# NetSync Gov — Setup SSL avec Let's Encrypt
# À exécuter sur le VPS après installation de Docker

DOMAIN=${1:-gov.netsync.bf}
EMAIL=${2:-edmondkolabou@gmail.com}

echo "=== Installation Certbot ==="
apt-get update && apt-get install -y certbot python3-certbot-nginx

echo "=== Obtention du certificat SSL ==="
certbot certonly --standalone \
  --agree-tos \
  --no-eff-email \
  --email $EMAIL \
  -d $DOMAIN

echo "=== Configuration auto-renouvellement ==="
echo "0 3 * * * certbot renew --quiet --post-hook 'docker compose -f /opt/netsync-gov/deploy/docker-compose.prod.yml restart nginx'" \
  | crontab -

echo "✓ SSL configuré pour $DOMAIN"
echo "  Certificat : /etc/letsencrypt/live/$DOMAIN/"
echo "  Renouvellement : automatique à 03h00 chaque jour"

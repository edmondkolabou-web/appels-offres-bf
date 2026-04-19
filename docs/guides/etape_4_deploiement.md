# Étape 4 — Lancer le déploiement Docker + SSL

> Prérequis : étape 3 terminée, .env.production rempli.
> Durée : 15 à 20 minutes.
> Le script fait TOUT automatiquement.

---

## 4a — Lancer le script de déploiement

```bash
# Se connecter au VPS
ssh root@185.XXX.XXX.XXX

# Aller dans le dossier
cd /opt/netsync_gov

# Rendre le script exécutable
chmod +x 13_Deploiement_Docker_VPS/scripts/deploy.sh

# Lancer le déploiement
./13_Deploiement_Docker_VPS/scripts/deploy.sh
```

### Ce que le script fait automatiquement (8 étapes)
1. Installe Docker, docker-compose, git, ufw
2. Configure le firewall (ports 22, 80, 443)
3. Clone/met à jour le code
4. Vérifie les variables d'environnement
5. Lance PostgreSQL + Redis + exécute les migrations Alembic
6. Obtient le certificat SSL Let's Encrypt (HTTPS gratuit)
7. Démarre tous les services (8 containers)
8. Vérifie que l'API et le frontend répondent

---

## 4b — Vérifier que les containers tournent

```bash
# Voir l'état de tous les services
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml ps

# Résultat attendu :
# NAME                STATUS          PORTS
# netsync_db          healthy         5432/tcp
# netsync_redis       healthy         6379/tcp
# netsync_api         healthy         0.0.0.0:8000->8000/tcp
# netsync_worker      running
# netsync_beat        running
# netsync_frontend    running         0.0.0.0:80->80/tcp
# netsync_nginx       running         0.0.0.0:443->443/tcp
# netsync_certbot     running
```

Tous les services doivent être en `healthy` ou `running`.
Si un service est en `Exit` ou `Restarting`, voir la section dépannage ci-dessous.

---

## 4c — Vérifier le SSL

```bash
# Tester HTTPS depuis le VPS
curl -I https://gov.netsync.bf
# Doit retourner : HTTP/2 200

curl -I https://api.gov.netsync.bf/health
# Doit retourner : HTTP/2 200
# Body : {"status": "ok", "service": "netsync-gov-api"}
```

---

## 4d — Vérifier les migrations Alembic

```bash
# Vérifier que toutes les tables ont été créées
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec db psql -U netsync -d netsync_gov -c "\dt"

# Résultat attendu (9 tables) :
# appels_offres
# abonnes
# preferences_alertes
# favoris
# paiements
# envois_alertes
# pipeline_logs
# equipes
# alembic_version
```

---

## 4e — Dépannage fréquent

### Un container est en "Restarting"
```bash
# Voir les logs du container problématique
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs api
# ou : logs worker / logs db / logs nginx

# Cause la plus fréquente : variable manquante dans .env.production
# Corriger → relancer :
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml up -d
```

### Le SSL n'a pas été obtenu
```bash
# Vérifier que le DNS pointe bien vers le VPS (étape 2)
dig gov.netsync.bf

# Relancer Certbot manuellement
docker run --rm \
  -v "$(pwd)/ssl_certs:/etc/letsencrypt" \
  -v "$(pwd)/ssl_www:/var/www/certbot" \
  certbot/certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email ton.email@gmail.com \
  --agree-tos --no-eff-email \
  -d gov.netsync.bf -d api.gov.netsync.bf
```

### Erreur "port already in use"
```bash
# Voir quel processus utilise le port 80 ou 443
lsof -i :80
lsof -i :443

# Arrêter Apache ou Nginx s'il est installé
systemctl stop apache2 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
systemctl disable apache2 2>/dev/null || true
systemctl disable nginx 2>/dev/null || true
```

---

**Si `curl https://gov.netsync.bf` retourne 200 → passer à l'étape 5.**

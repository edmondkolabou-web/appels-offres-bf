# NetSync Gov — Référence rapide des commandes

## Connexion au VPS
```bash
ssh root@IP_DU_VPS
cd /opt/netsync_gov
```

## État des services
```bash
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml ps
```

## Logs en temps réel
```bash
# Tous les services
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs -f

# Un service spécifique
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs -f api
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs -f worker
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml logs -f nginx
```

## Démarrer / Arrêter / Redémarrer
```bash
# Démarrer tout
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml up -d

# Arrêter tout (données conservées)
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml down

# Redémarrer un service
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml restart api
```

## Mettre à jour le code
```bash
cd /opt/netsync_gov
./13_Deploiement_Docker_VPS/scripts/update.sh
```

## Déclencher le pipeline manuellement
```bash
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 -c "from pipeline.pipeline import run_pipeline; run_pipeline.delay()"
```

## Accès à la base de données
```bash
# Ouvrir psql
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec db psql -U netsync -d netsync_gov

# Commandes SQL utiles
# Compter les AOs
SELECT COUNT(*) FROM appels_offres;

# AOs du jour
SELECT titre, secteur, date_cloture FROM appels_offres
WHERE date_publication = CURRENT_DATE ORDER BY created_at DESC;

# Abonnés par plan
SELECT plan, COUNT(*) FROM abonnes GROUP BY plan;

# MRR actuel
SELECT SUM(CASE WHEN plan='pro' THEN 15000 ELSE 0 END) +
       SUM(CASE WHEN plan='equipe' THEN 45000 ELSE 0 END) AS mrr_fcfa
FROM abonnes WHERE plan != 'gratuit';
```

## Backup de la base de données
```bash
# Créer un backup
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec db pg_dump -U netsync netsync_gov > backup_$(date +%Y%m%d_%H%M).sql

# Lister les backups
ls -lh backup_*.sql
```

## Monitoring
```bash
# Lancer le healthcheck
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 13_Deploiement_Docker_VPS/monitoring/healthcheck.py

# Ajouter au cron (toutes les 5 minutes)
crontab -e
# Ajouter cette ligne :
# */5 * * * * cd /opt/netsync_gov && docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml exec -T api python3 13_Deploiement_Docker_VPS/monitoring/healthcheck.py >> /var/log/netsync_health.log 2>&1
```

## Renouvellement SSL (automatique)
```bash
# Forcer le renouvellement si besoin
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec certbot certbot renew --force-renewal
```

## Lancer les tests
```bash
docker compose -f 13_Deploiement_Docker_VPS/docker-compose.prod.yml \
  exec api python3 -m pytest 14_Consolidation_Tests_Securite/ -v
```

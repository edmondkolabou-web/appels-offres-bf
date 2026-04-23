#!/bin/bash
# NetSync Gov — Backup automatique PostgreSQL
# Cron recommandé : 0 2 * * * /opt/netsync-gov/deploy/backup-db.sh

BACKUP_DIR="/opt/netsync-gov/backups"
DB_CONTAINER="netsync_db"
DB_NAME="netsync_gov"
DB_USER="netsync"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/netsync_gov_${TIMESTAMP}.sql.gz"

echo "[$(date)] Début backup PostgreSQL..."

# Dump compressé
docker exec $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

if [ $? -eq 0 ]; then
    SIZE=$(du -h $BACKUP_FILE | cut -f1)
    echo "[$(date)] ✓ Backup réussi : $BACKUP_FILE ($SIZE)"

    # Supprimer les backups de plus de N jours
    find $BACKUP_DIR -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
    REMAINING=$(ls -1 $BACKUP_DIR/*.sql.gz 2>/dev/null | wc -l)
    echo "[$(date)] Backups conservés : $REMAINING (rétention $RETENTION_DAYS jours)"
else
    echo "[$(date)] ✗ ERREUR backup !"
    exit 1
fi

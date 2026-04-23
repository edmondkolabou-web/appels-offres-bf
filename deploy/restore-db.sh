#!/bin/bash
# NetSync Gov — Restauration PostgreSQL depuis backup
# Usage : ./restore-db.sh backups/netsync_gov_20260423_020000.sql.gz

BACKUP_FILE=$1
DB_CONTAINER="netsync_db"
DB_NAME="netsync_gov"
DB_USER="netsync"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <fichier_backup.sql.gz>"
    echo "Backups disponibles :"
    ls -lh /opt/netsync-gov/backups/*.sql.gz 2>/dev/null
    exit 1
fi

echo "⚠ ATTENTION : cette opération va REMPLACER toute la base de données !"
echo "Fichier : $BACKUP_FILE"
read -p "Continuer ? (oui/non) " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    echo "Annulé."
    exit 0
fi

echo "[$(date)] Restauration en cours..."
gunzip -c $BACKUP_FILE | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME

if [ $? -eq 0 ]; then
    echo "[$(date)] ✓ Restauration réussie"
else
    echo "[$(date)] ✗ ERREUR restauration !"
    exit 1
fi

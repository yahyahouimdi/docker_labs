#!/bin/sh
set -e

DB_PATH="${DB_PATH:-/data/access.db}"

# 1. Création du fichier SQLite et du schéma (idempotent)
sqlite3 "$DB_PATH" < /db/init.sql
echo "SQLite database ready: $DB_PATH"

# 2. Interface d'administration protégée par mot de passe.
#    Le mot de passe est lu depuis le secret Docker (fichier monté en lecture seule)
#    et n'apparaît ni dans l'image, ni dans docker-compose.yml, ni dans "docker inspect".
SQLITE_WEB_PASSWORD="$(cat /run/secrets/db_admin_password)"
export SQLITE_WEB_PASSWORD

exec sqlite_web --host 0.0.0.0 --port 8080 --no-browser --password "$DB_PATH"

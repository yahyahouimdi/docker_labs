# Conteneur de la base SQLite : crée le schéma et expose sqlite-web (admin protégé)
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir sqlite-web==0.6.4

# Même UID que apiuser (1000) pour que les deux conteneurs puissent écrire dans /data
RUN useradd -m -u 1000 -s /bin/sh dbuser

WORKDIR /db
COPY init.sql entrypoint.sh ./
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh \
    && mkdir -p /data && chown -R dbuser:dbuser /data

USER dbuser

ENV DB_PATH=/data/access.db

# Les données vivent dans un volume nommé (persistance)
VOLUME ["/data"]

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=5 --start-period=3s \
  CMD sqlite3 "$DB_PATH" "SELECT 1 FROM access_log LIMIT 1;" > /dev/null || exit 1

ENTRYPOINT ["/db/entrypoint.sh"]

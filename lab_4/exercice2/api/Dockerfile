# Books API du Lab03 (Dockerfile-logs) + accès à la base SQLite
FROM python:3.11-slim

# UID fixe (1000), identique à celui du conteneur db, pour partager le volume /data
RUN useradd -m -u 1000 -s /bin/bash apiuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Répertoires de logs et de données appartenant à apiuser
RUN mkdir -p /var/log/api /data && chown -R apiuser:apiuser /var/log/api /data /app

USER apiuser

ENV DB_PATH=/data/access.db

EXPOSE 5000

HEALTHCHECK --interval=5s --timeout=3s --retries=5 --start-period=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=2)"

CMD ["python", "app.py"]

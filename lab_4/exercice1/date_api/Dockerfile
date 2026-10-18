# Image commune aux API Date_en et Date_fr (basée sur Dockerfile-logs du Lab03)
FROM python:3.11-slim

# Création de l'utilisateur non-root
RUN useradd -m -s /bin/bash apiuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Répertoire de logs appartenant à apiuser
RUN mkdir -p /var/log/api && chown -R apiuser:apiuser /var/log/api /app

USER apiuser

# Langue par défaut, surchargée dans docker-compose.yml
ENV DATE_LANG=en

EXPOSE 5000

HEALTHCHECK --interval=5s --timeout=3s --retries=5 --start-period=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=2)"

CMD ["python", "app.py"]

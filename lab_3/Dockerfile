# Utiliser l'image Python officielle comme base
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur

WORKDIR /app
# Copier d'abord requirements (pour un meilleur cache)
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . .

# Exposer le port 5000
EXPOSE 5000

# Définir les variables d'environnement
ENV PYTHONPATH=/app

# Exécuter l'application
CMD ["python", "app.py"]
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from datetime import datetime
from babel.dates import format_date, format_time
import os

# ─────────────────────────────────────────
# 1. Création de l'application Flask
#    La langue servie (en / fr) est fixée par la variable DATE_LANG,
#    ce qui permet de construire les deux API à partir du même code.
# ─────────────────────────────────────────
app = Flask(__name__)

LANG = os.environ.get("DATE_LANG", "en")

# ─────────────────────────────────────────
# 2. Configuration du logging vers fichier (repris du Lab03)
# ─────────────────────────────────────────
log_dir = "/var/log/api"
os.makedirs(log_dir, exist_ok=True)

handler = RotatingFileHandler(
    os.path.join(log_dir, f"date_{LANG}.log"),
    maxBytes=1_000_000,
    backupCount=3
)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.info(f"Date API startup (lang={LANG})")

# ─────────────────────────────────────────
# 3. Routes
# ─────────────────────────────────────────
@app.route('/')
def home():
    app.logger.info("GET /")
    return jsonify({
        "message": f"Welcome to the Date_{LANG} API",
        "lang": LANG,
        "endpoints": {
            "GET /date": "Current date in the API language",
            "GET /health": "Health check"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "lang": LANG,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/date')
def get_date():
    now = datetime.now()
    app.logger.info("GET /date")
    return jsonify({
        "lang": LANG,
        "date": format_date(now, format="full", locale=LANG),
        "time": format_time(now, format="medium", locale=LANG),
        "service": os.environ.get("HOSTNAME", "unknown")
    })

# ─────────────────────────────────────────
# 4. Démarrage
# ─────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)

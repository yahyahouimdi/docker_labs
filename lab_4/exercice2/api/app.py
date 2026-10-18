import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from datetime import datetime
import hmac
import os
import sqlite3

# ─────────────────────────────────────────
# 1. Création de l'application Flask
#    (UNE SEULE FOIS, tout en haut)
# ─────────────────────────────────────────
app = Flask(__name__)

# ─────────────────────────────────────────
# 2. Configuration du logging vers fichier
# ─────────────────────────────────────────
log_dir = "/var/log/api"
os.makedirs(log_dir, exist_ok=True)

handler = RotatingFileHandler(
    os.path.join(log_dir, "api.log"),
    maxBytes=1_000_000,
    backupCount=3
)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.info("API startup")

# ─────────────────────────────────────────
# 3. Base SQLite des accès (Lab04 - Exercice 2)
#    Le fichier est sur le volume partagé avec le conteneur "db",
#    qui crée la table access_log au démarrage.
# ─────────────────────────────────────────
DB_PATH = os.environ.get("DB_PATH", "/data/access.db")
ADMIN_PASSWORD_FILE = os.environ.get("ADMIN_PASSWORD_FILE", "/run/secrets/api_admin_password")

def get_db():
    return sqlite3.connect(DB_PATH, timeout=5)

def read_admin_password():
    # Le mot de passe est fourni par un secret Docker, jamais en dur ni en variable d'env
    with open(ADMIN_PASSWORD_FILE) as f:
        return f.read().strip()

@app.before_request
def log_access():
    # A chaque accès au backend : date + adresse IP du client
    if request.path == '/health':
        return
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO access_log (accessed_at, client_ip, method, path) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(timespec='seconds'), request.remote_addr,
                 request.method, request.path)
            )
    except sqlite3.Error as e:
        app.logger.error(f"access_log insert failed: {e}")

# ─────────────────────────────────────────
# 4. Base de données en mémoire
# ─────────────────────────────────────────
books = [
    {"id": 1, "title": "1984", "author": "George Orwell", "year": 1949},
    {"id": 2, "title": "To Kill a Mockingbird", "author": "Harper Lee", "year": 1960},
    {"id": 3, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "year": 1925}
]

# ─────────────────────────────────────────
# 5. Routes
# ─────────────────────────────────────────
@app.route('/')
def home():
    app.logger.info("GET /")
    return jsonify({
        "message": "Welcome to the Books API",
        "version": "1.0",
        "endpoints": {
            "GET /books": "List all books",
            "GET /books/<id>": "Get a specific book",
            "POST /books": "Add a new book",
            "PUT /books/<id>": "Update a book",
            "DELETE /books/<id>": "Delete a book",
            "GET /health": "Health check",
            "GET /access-logs": "Last accesses (HTTP Basic auth: admin)"
        }
    })

@app.route('/health')
def health():
    app.logger.info("GET /health")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/books', methods=['GET'])
def get_books():
    app.logger.info("GET /books")
    return jsonify({"books": books, "count": len(books)})

@app.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if book:
        app.logger.info(f"GET /books/{book_id} - found")
        return jsonify(book)
    app.logger.error(f"GET /books/{book_id} - not found")
    return jsonify({"error": "Book not found"}), 404

@app.route('/books', methods=['POST'])
def add_book():
    if not request.json or not all(k in request.json for k in ['title', 'author', 'year']):
        app.logger.error("POST /books - missing required fields")
        return jsonify({"error": "Missing required fields"}), 400

    new_book = {
        "id": max([b["id"] for b in books]) + 1 if books else 1,
        "title": request.json['title'],
        "author": request.json['author'],
        "year": request.json['year']
    }
    books.append(new_book)
    app.logger.info(f"POST /books - added id={new_book['id']} title={new_book['title']}")
    return jsonify(new_book), 201

@app.route('/books/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        app.logger.error(f"PUT /books/{book_id} - not found")
        return jsonify({"error": "Book not found"}), 404

    if request.json:
        book.update({k: v for k, v in request.json.items() if k in ['title', 'author', 'year']})
    app.logger.info(f"PUT /books/{book_id} - updated")
    return jsonify(book)

@app.route('/books/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    global books
    book = next((b for b in books if b["id"] == book_id), None)
    if not book:
        app.logger.error(f"DELETE /books/{book_id} - not found")
        return jsonify({"error": "Book not found"}), 404

    books = [b for b in books if b["id"] != book_id]
    app.logger.info(f"DELETE /books/{book_id} - deleted")
    return jsonify({"message": "Book deleted successfully"})

@app.route('/access-logs', methods=['GET'])
def access_logs():
    auth = request.authorization
    if not auth or auth.username != "admin" or not hmac.compare_digest(
            (auth.password or "").encode(), read_admin_password().encode()):
        app.logger.error("GET /access-logs - unauthorized")
        return jsonify({"error": "Unauthorized"}), 401, {"WWW-Authenticate": 'Basic realm="access-logs"'}

    limit = request.args.get('limit', 50, type=int)
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, accessed_at, client_ip, method, path FROM access_log ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    app.logger.info("GET /access-logs")
    return jsonify({"accesses": [dict(r) for r in rows], "total": total})

# ─────────────────────────────────────────
# 6. Démarrage
#    debug=False pour éviter le double log
# ─────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
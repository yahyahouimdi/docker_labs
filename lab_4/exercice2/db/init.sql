-- Table des accès au backend : date + adresse IP du client
CREATE TABLE IF NOT EXISTS access_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    accessed_at TEXT    NOT NULL,
    client_ip   TEXT    NOT NULL,
    method      TEXT,
    path        TEXT
);

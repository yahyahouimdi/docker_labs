# Lab 4 - Docker Compose

Both exercises build on the Flask code and Dockerfiles from [`lab_3/`](../lab_3) (non-root `apiuser`, file logging in `/var/log/api`).

## Prerequisites

- Docker Desktop with Docker Compose
- Host ports `8080` (exercise 1), `5000` and `8081` (exercise 2) available

## Exercise 1 - Date web application (en / fr)

```
Browser ──► proxy (Nginx :8080) ──┬── /          ──► frontend (HTML + JS)
                                  ├── /api/en/   ──► date_en (Flask, DATE_LANG=en)
                                  └── /api/fr/   ──► date_fr (Flask, DATE_LANG=fr)
```

| Path | Role |
| --- | --- |
| `exercice1/frontend/index.html` | Web page with the `en` / `fr` buttons; calls `/api/<lang>/date` with `fetch` |
| `exercice1/proxy/nginx.conf` | Reverse proxy routing to the frontend or to the target API |
| `exercice1/date_api/` | Flask date API (based on the Lab 3 API). One image, the language is set by the `DATE_LANG` variable |
| `exercice1/docker-compose.yml` | Deploys the four services; only the proxy is published on the host |

Run it:

```powershell
docker compose -f lab_4/exercice1/docker-compose.yml up -d --build --wait
```

Open <http://localhost:8080> and click `en` or `fr`. The APIs can also be called through the proxy:

```powershell
curl.exe http://localhost:8080/api/en/date
# {"date":"Sunday, October 18, 2026","lang":"en",...}
curl.exe http://localhost:8080/api/fr/date
# {"date":"dimanche 18 octobre 2026","lang":"fr",...}
```

Stop it:

```powershell
docker compose -f lab_4/exercice1/docker-compose.yml down
```

## Exercise 2 - Lab 3 API + SQLite

Every request to the Books API (except `/health`) inserts the date and the client IP address into the `access_log` table of a SQLite database.

| Service | Role |
| --- | --- |
| `db` | Creates the SQLite file and the `access_log` table (`db/init.sql`), then serves the [sqlite-web](https://github.com/coleifer/sqlite-web) admin UI, protected by a password, on `127.0.0.1:8081` |
| `api` | Lab 3 Books API. A `before_request` hook writes `(accessed_at, client_ip, method, path)` to the database. `GET /access-logs` returns the latest accesses and requires HTTP Basic auth |

### Data persistence

- The database lives in the named volume `sqlite-data`, mounted on `/data` in both containers. It survives `docker compose down`, rebuilds, and container re-creation. Only `docker compose down -v` deletes it.
- The API logs are kept in the named volume `api-logs`.
- Both images use the same UID (1000) so both containers can write to the shared volume while running as non-root users.

### Password protection

- The passwords are **Docker secrets** (`secrets:` in `docker-compose.yml`). They are mounted read-only in `/run/secrets/<name>` and are never in the images, in `docker-compose.yml`, or in environment variables, so `docker inspect` does not show them.
- The real secret files `secrets/*.txt` are ignored by git (`exercice2/.gitignore`). Only the `*.txt.example` templates are committed.
- The API compares the password with `hmac.compare_digest` (constant time).
- The admin UI is published on `127.0.0.1` only, so it cannot be reached from another machine.

### Run it

Create the secret files from the templates and choose your own passwords:

```powershell
cd lab_4/exercice2
Copy-Item secrets/db_admin_password.txt.example secrets/db_admin_password.txt
Copy-Item secrets/api_admin_password.txt.example secrets/api_admin_password.txt
# edit both files, then:
docker compose up -d --build --wait
```

Generate some traffic and read the access table:

```powershell
curl.exe http://localhost:5000/books
curl.exe http://localhost:5000/books/1
curl.exe -u admin:<api password> http://localhost:5000/access-logs
```

Example response:

```json
{"accesses":[{"accessed_at":"2026-10-18T08:21:47","client_ip":"172.18.0.1","id":2,"method":"GET","path":"/books/1"},
             {"accessed_at":"2026-10-18T08:21:47","client_ip":"172.18.0.1","id":1,"method":"GET","path":"/books"}],"total":2}
```

The Lab 3 test script also works: `python api/test_api.py`.

Browse the database at <http://localhost:8081> (password from `secrets/db_admin_password.txt`), or query it from the container:

```powershell
docker compose exec db sqlite3 /data/access.db "SELECT * FROM access_log ORDER BY id DESC LIMIT 10;"
```

Check persistence:

```powershell
docker compose down
docker compose up -d --wait
curl.exe -u admin:<api password> "http://localhost:5000/access-logs?limit=1"   # "total" keeps growing
```

Note: with Docker Desktop, requests from the host reach the container through the Docker network gateway, so the stored IP is `172.x.0.1`. Requests from other containers or from other machines on a Linux host show their real address.

Stop it (keep the data), or stop it and delete the data:

```powershell
docker compose down
docker compose down -v
```

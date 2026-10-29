# Exam Lab - Microservices with Docker Compose

A microservices stack with five services: a reverse proxy, an API, a background worker, a database and a cache.

## 1. Architecture

```
                 Host machine
                      │  http://localhost:8080
                      ▼
 ┌──────────── network "frontend" ────────────┐
 │   proxy (Nginx :80)  ───────►  api (:3000) │
 └────────────────────────────────────│───────┘
                                      │  (api is on BOTH networks)
 ┌──────────── network "backend" (internal: no Internet) ───────┐
 │   api ───► db (PostgreSQL :5432)                              │
 │   api ───► cache (Redis :6379)                                │
 │   worker x N ───► db / cache                                  │
 └───────────────────────────────────────────────────────────────┘
```

| Service | Image | Role | Networks | Published port |
| --- | --- | --- | --- | --- |
| `proxy` | `nginx:1.27-alpine` | Single public entry point, forwards every request to the API | `frontend` | `8080 -> 80` |
| `api` | built from `api/Dockerfile` | Web service on port 3000 (simulated with `python3 -m http.server`) | `frontend` + `backend` | none |
| `worker` | built from `worker/Dockerfile` | Background loop that processes tasks (simulated) | `backend` | none |
| `db` | `postgres:16-alpine` | Persistent data, stored in the `db-data` volume | `backend` | none |
| `cache` | `redis:7-alpine` | In-memory key-value store | `backend` | none |

## 2. Files

```
exam-lab/
├── .env                 # variables (DB credentials, proxy port, worker count)
├── docker-compose.yml   # the five services, networks, volume
├── nginx.conf           # reverse proxy configuration
├── api/Dockerfile       # given with the lab
└── worker/Dockerfile    # given with the lab
```

The two Dockerfiles were provided. The three files created for the exam are `.env`, `docker-compose.yml` and `nginx.conf`.

### 2.1 `.env`

Docker Compose reads this file automatically when it sits next to `docker-compose.yml`. Every `${VAR}` in the compose file is replaced by its value.

```env
POSTGRES_USER=examuser
POSTGRES_PASSWORD=exampassword
POSTGRES_DB=examdb
PROXY_PORT=8080
WORKER_REPLICAS=2
```

Keeping these values out of the compose file means you can change them (a password or the port, for example) without touching the configuration. Run `docker compose config` to see the file after the variables are replaced.

### 2.2 `nginx.conf`

```nginx
upstream api_backend {
    server api:3000;          # "api" = service name, resolved by Docker's DNS
}

server {
    listen 80;

    location /nginx-health {  # used by the proxy healthcheck
        return 200 "ok\n";
    }

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

- The file is mounted read-only on `/etc/nginx/conf.d/default.conf`, so it replaces Nginx's default site.
- `api` works as a hostname because Docker runs an internal DNS server. On a user-defined network, each service name resolves to the IP address of its container.
- The `X-Real-IP` and `X-Forwarded-For` headers pass the real client IP to the API. Without them, the API would only see the proxy's IP address.

### 2.3 `docker-compose.yml`: the main ideas

**a) Healthchecks.** Each service has a command that Docker runs regularly to check whether the service really works, not only whether its process is running:

| Service | Healthcheck |
| --- | --- |
| db | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` |
| cache | `redis-cli ping` (answers `PONG`) |
| api | `curl -f http://localhost:3000/` (curl is installed in the api Dockerfile for this) |
| proxy | `wget -qO- http://127.0.0.1/nginx-health` |

In the db healthcheck, the `$$` in `$${POSTGRES_USER}` stops Compose from replacing the variable. The variable is read inside the container instead.

**b) Startup order: `depends_on` + `condition: service_healthy`.**

```
db, cache  ──(healthy)──►  api, worker  ──(api healthy)──►  proxy
```

A plain `depends_on: [db]` only waits until the db container has started, and PostgreSQL can still be initialising at that point. With `condition: service_healthy`, Compose waits until the healthcheck passes.

**c) Network isolation: two networks.**

- `frontend`: `proxy` and `api`.
- `backend` with `internal: true`: `api`, `worker`, `db` and `cache`. An `internal` network has no route to the outside world, so containers on it cannot reach the Internet and cannot publish ports.
- `api` is the only service on both networks. It acts as the bridge between them.
- Only `proxy` has a `ports:` entry. `db`, `cache`, `api` and `worker` cannot be reached from the host.

**d) Resource limits on the API.**

```yaml
deploy:
  resources:
    limits:       { cpus: "0.50", memory: 256M }   # hard maximum
    reservations: { cpus: "0.25", memory: 128M }   # guaranteed minimum
```

- `limits.cpus: 0.50`: the API can use at most half of one CPU core.
- `limits.memory: 256M`: if the API uses more than this, the kernel stops it (OOM kill).
- `reservations` is the minimum the API keeps when the host is under load.

**e) Scaling the worker.**

```yaml
worker:
  deploy:
    replicas: ${WORKER_REPLICAS}   # 2 by default
```

The worker has no `container_name` and no `ports`. Both would block scaling, because two containers cannot share a name or a host port. Compose names the copies `exam-lab-worker-1`, `-2`, and so on.

**f) Persistence.** The `db-data` named volume holds `/var/lib/postgresql/data`. The data survives `docker compose down`. Only `docker compose down -v` deletes it.

## 3. Run it

```powershell
cd exam-lab
docker compose up -d --build --wait   # --wait = return when every service is healthy
docker compose ps
```

Expected output: `db`, `cache`, `api` and `proxy` are `(healthy)`, two workers are `Up`, and only the proxy shows `0.0.0.0:8080->80/tcp`.

Open <http://localhost:8080>. The API, reached through Nginx, shows a directory listing.

Stop it:

```powershell
docker compose down        # keeps the database volume
docker compose down -v     # also deletes the database volume
```

## 4. Validation tests (results from a real run)

### Test 1: startup order

```powershell
docker compose up -d --wait        # watch the order in the output
docker compose ps
docker inspect --format "{{.Name}} {{.State.StartedAt}}" exam-lab-db-1 exam-lab-cache-1 exam-lab-api-1 exam-lab-worker-1 exam-lab-proxy-1
```

Result:

```
/exam-lab-cache-1   08:12:47.875
/exam-lab-db-1      08:12:47.878
/exam-lab-api-1     08:12:53.618   <- about 6 s later, once db and cache are healthy
/exam-lab-worker-1  08:12:53.821
/exam-lab-proxy-1   08:12:59.379   <- about 6 s later, once the api is healthy
```

During `up`, Compose prints `Container exam-lab-api-1 Waiting` and then `Healthy` before it starts the proxy. This shows that the `depends_on` conditions are applied.

### Test 2: network isolation

```powershell
# which networks each container is on
docker inspect --format "{{.Name}}: {{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}" $(docker compose ps -q)

# allowed paths
curl.exe http://localhost:8080/                          # host -> proxy: 200
docker compose exec proxy  wget -qO- http://api:3000/    # proxy -> api: OK
docker compose exec api    nc -zw3 db 5432               # api -> db: OK
docker compose exec worker nc -zw3 cache 6379            # worker -> cache: OK

# blocked paths
docker compose exec proxy  nc -zw3 db 5432               # nc: bad address 'db'
docker compose exec worker nc -zw3 proxy 80              # nc: bad address 'proxy'
docker compose exec worker wget -T 5 http://example.com  # fails: no Internet
docker compose port db 5432                              # nothing published
```

| From → To | Result | Why |
| --- | --- | --- |
| host → proxy :8080 | ✅ HTTP 200 | only published port |
| proxy → api | ✅ | both on `frontend` |
| proxy → db / cache | ❌ `bad address` | proxy is not on `backend`, so DNS does not even know the name |
| api → db / cache | ✅ | api is on `backend` |
| worker → cache | ✅ | both on `backend` |
| worker → proxy | ❌ `bad address` | worker is not on `frontend` |
| worker → Internet | ❌ | `backend` is `internal: true` |
| host → db / cache / api | ❌ | no `ports:` |

### Test 3: resource limits of the API

```powershell
docker inspect exam-lab-api-1 --format "NanoCpus={{.HostConfig.NanoCpus}} Memory={{.HostConfig.Memory}} MemoryReservation={{.HostConfig.MemoryReservation}}"
docker stats --no-stream exam-lab-api-1
```

Result:

```
NanoCpus=500000000  Memory=268435456  MemoryReservation=134217728
exam-lab-api-1   0.03%   11.53MiB / 256MiB
```

- `NanoCpus` is in billionths of a CPU: 500000000 / 10^9 = **0.5 CPU**.
- `Memory` is in bytes: 268435456 = 256 × 1024 × 1024 = **256 MiB**.
- `MemoryReservation`: 134217728 = **128 MiB**.
- `docker stats` shows `/ 256MiB` as the memory limit. Without a limit, it would show the whole RAM of the Docker VM.

### Test 4: scaling the workers while the stack runs

```powershell
docker compose up -d --scale worker=5 --no-recreate   # scale up
docker compose ps worker
docker compose up -d --scale worker=1 --no-recreate   # scale down
docker compose ps worker
```

`--no-recreate` tells Compose not to touch containers that already exist. It only adds or removes worker containers.

What the run showed:

- Scale up: `worker-1` and `worker-2` stayed `Running`, and `worker-3`, `-4` and `-5` were `Created` and then `Started`.
- Scale down: `worker-2` to `worker-5` were `Stopped` and then `Removed`, and `worker-1` kept running.
- The IDs of the `db`, `cache`, `api` and `proxy` containers were **the same before and after**, so none of them were restarted.
- A loop calling `http://localhost:8080/` 30 times during the scaling returned **30 × HTTP 200**, with no interruption.

To change the default number of workers, edit `WORKER_REPLICAS` in `.env`.

## 5. Presentation script (about 5 minutes)

1. **Goal (30 s).** "A microservices stack with five services. Only Nginx is public. The API is the only bridge between the public and private sides."
2. **Draw the diagram (1 min).** Two networks. The API sits on both. The backend is `internal`.
3. **Files (1 min).** `.env` holds the variables, `nginx.conf` holds the reverse proxy, and `docker-compose.yml` holds the services, healthchecks, `depends_on`, networks, limits, replicas and volume.
4. **Live demo (2–3 min).**
   - `docker compose up -d --build --wait`, then show the `Waiting` → `Healthy` order (test 1).
   - `curl.exe localhost:8080`, then `docker compose exec proxy nc -zw3 db 5432`, which fails with `bad address` (test 2).
   - `docker inspect ... NanoCpus/Memory` and `docker stats` (test 3).
   - `docker compose up -d --scale worker=5 --no-recreate`, then `ps` (test 4).
5. **Conclusion.** Security comes from least exposure plus network segmentation. Reliability comes from healthchecks. Scalability comes from stateless workers.

## 6. Likely questions from the professor

**Why two networks and not one?**
With one network, any compromised container (the proxy, for example) could connect directly to PostgreSQL. With two networks, an attacker would first have to compromise the API. This is defence in depth.

**What does `internal: true` do?**
Docker creates the network without a gateway to the outside. Containers on it can talk to each other but cannot reach the Internet, and the host cannot reach them through published ports.

**`depends_on` vs `condition: service_healthy`?**
A plain `depends_on` waits for the container to *start*. `service_healthy` waits for the *healthcheck to pass*, which means the service is actually ready, for example when PostgreSQL accepts connections.

**What happens if the API uses more than 256 MB?**
The kernel's OOM killer stops it, and `docker inspect` shows `OOMKilled: true`. A CPU limit never kills the container. It is throttled instead.

**Limits vs reservations?**
`limits` is the maximum the container can use. `reservations` is the minimum it keeps when the host is under pressure.

**Why can the worker be scaled but not the API as-is?**
The worker has no `container_name` and no published port, and it is stateless. The API could also be scaled, because it has no published port. Nginx would then need to load-balance across the copies (Docker's DNS returns every copy's IP).

**Why can the db not be scaled the same way?**
PostgreSQL has state on a volume. Two instances writing to the same data directory would corrupt it. Scaling a database needs replication (primary and replicas), not more copies of the same container.

**Why did workers take about 10 s to stop when scaling down?**
The worker's command is `sh -c "while ...; sleep 10"`. The shell runs as PID 1 and ignores `SIGTERM`, so Docker waits for the 10 s grace period and then sends `SIGKILL`. The fix is to handle the signal (`trap 'exit 0' TERM`) or to add `init: true` to the service.

**Why does the proxy healthcheck use `127.0.0.1` and not `localhost`?**
In the Alpine image, `localhost` first resolves to IPv6 `::1`, but Nginx only listens on IPv4 (`listen 80;`). The first version used `localhost`, and the proxy stayed `unhealthy` with "Connection refused". Changing to `127.0.0.1` fixed it. (Another fix is to add `listen [::]:80;`.)

**How does the proxy find the API?**
Through Docker's embedded DNS server (`127.0.0.11`). On a user-defined network, the service name `api` resolves to its container's IP.

**Where is the password? Is that secure?**
It is in `.env`, which is fine for a lab. In production, use Docker secrets (`POSTGRES_PASSWORD_FILE`) and keep `.env` out of git, as in Lab 4 exercise 2.

**Is the data kept after `docker compose down`?**
Yes. It is in the `db-data` named volume. Only `down -v` removes it.

# Docker Labs

Practical Docker and containerisation exercises for the virtualisation module.

## Repository Contents

- `Lab_1/`: Lab 1 written work and responses.
- `Lab_2/`: Containerised web application exercises.
  - `question1/`: Static Apache web page and Dockerfile.
  - `question3/`: Notes about container filesystem isolation.
  - `question4/`: Nginx load balancer and Docker Compose stack.
  - `question5/`: Flask date API.
  - `benchmark/`: ApacheBench container for load testing.

- `lab_3/`: Flask Books API with a non-root user and file logging.
- `lab_4/`: Docker Compose exercises built on Lab 3.
  - `exercice1/`: Date web app (HTML + JS frontend, Nginx reverse proxy, `en` and `fr` Flask APIs).
  - `exercice2/`: Lab 3 API that logs every access (date + client IP) to a persistent SQLite database, with passwords stored as Docker secrets.

For the detailed Lab 2 instructions and question notes, see [`Lab_2/README.md`](Lab_2/README.md). For Lab 4, see [`lab_4/README.md`](lab_4/README.md).

## Prerequisites

- Docker Desktop with Docker Compose
- A web browser
- PowerShell, or an equivalent terminal
- Host ports `5000` and `8080` available for the complete Lab 2 stack

## Run Lab 2

From the repository root, build the services:

```powershell
docker compose -f Lab_2/question4/docker-compose.yml build
```

Start the Apache instances, Flask API, and Nginx load balancer:

```powershell
docker compose -f Lab_2/question4/docker-compose.yml up -d instance1 instance2 dateservice lb
```

Open the application in a browser:

<http://localhost:8080>

Test the date API directly:

```powershell
curl.exe "http://localhost:5000/date?lang=en"
curl.exe "http://localhost:5000/date?lang=fr"
```

Run the benchmark after the services become healthy:

```powershell
docker compose -f Lab_2/question4/docker-compose.yml run --rm benchmarker
```

Stop and remove the containers and network:

```powershell
docker compose -f Lab_2/question4/docker-compose.yml down
```

## Run Individual Services

Build and run the static Apache page on port `8081`:

```powershell
docker build -t docker-labs-apache Lab_2/question1
docker run --rm -p 8081:80 docker-labs-apache
```

Then open <http://localhost:8081>.

Build and run the Flask date service on port `5000`:

```powershell
docker build -t docker-labs-date Lab_2/question5
docker run --rm -p 5000:5000 docker-labs-date
```

## Learning Topics

- Building images with Dockerfiles
- Serving static content with Apache
- Running a Python Flask service in a container
- Container filesystem isolation
- Reverse proxying and load balancing with Nginx
- Service health checks and startup dependencies in Docker Compose
- HTTP load testing with ApacheBench

## Cleanup

The Compose cleanup command removes the Lab 2 containers and network:

```powershell
docker compose -f Lab_2/question4/docker-compose.yml down
```

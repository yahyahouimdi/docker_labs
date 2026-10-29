FROM alpine:3.18
RUN apk add --no-cache curl python3
WORKDIR /app
# On simule une API qui écoute sur le port 3000 et répond au healthcheck
CMD python3 -m http.server 3000

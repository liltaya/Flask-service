# Flask API with PostgreSQL in Docker Compose

```bash
cp .env.docker.example .env.docker
nano .env.docker

docker compose --env-file .env.docker config
docker compose --env-file .env.docker up -d --build
docker compose --env-file .env.docker ps

curl -fsS http://127.0.0.1:5000/health
curl -fsS http://127.0.0.1:5000/metrics | head
```

Logs:

```bash
docker compose --env-file .env.docker logs --tail=100 api
docker compose --env-file .env.docker logs --tail=100 db
```

Stop without deleting PostgreSQL data:

```bash
docker compose --env-file .env.docker down
```

Delete containers and PostgreSQL volume:

```bash
docker compose --env-file .env.docker down -v
```

Host Nginx can continue proxying to `http://127.0.0.1:5000`.
Host Prometheus can continue scraping `127.0.0.1:5000/metrics`.

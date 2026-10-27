# README

# Flask Service: Operational Data Platform and Log Analyzer

!CI

Python

Flask

PostgreSQL

Docker

A REST API built with Flask, SQLAlchemy and PostgreSQL, deployed on Linux behind Nginx and systemd (or Docker Compose), with Prometheus metrics for Grafana. The repository also includes a command-line log analyzer for Nginx and Apache access logs.

## Features

- CRUD REST endpoints with PostgreSQL persistence
- JSON input validation and structured JSON errors
- Health endpoint that checks the database
- Prometheus metrics, ready for Grafana dashboards
- Nginx reverse proxy and systemd service
- Automated Bash deployment, or Docker Compose
- Command-line access-log analyzer with text, JSON and CSV reports
- CI with linting, type checking, tests and coverage

## Architecture

```
Client --> Nginx --> Flask API (systemd or Docker Compose) --> PostgreSQL
                          |
                      /metrics --> Prometheus --> Grafana
```

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/` | API information |
| GET | `/health` | Application and database health |
| GET | `/metrics` | Prometheus metrics |
| GET | `/items` | List all items |
| GET | `/items/<id>` | Get an item |
| POST | `/items` | Create an item |
| PUT | `/items/<id>` | Update an item |
| DELETE | `/items/<id>` | Delete an item |

## Requirements

- Ubuntu Linux
- PostgreSQL
- Python 3
- Nginx
- systemd
- Git

The deployment script installs the required operating-system packages and Python dependencies.

## Environment configuration

Create `/opt/flask-service/.env`:

```bash
DATABASE_URL=postgresql+psycopg://flask_service_user:password@127.0.0.1:5432/flask_service
```

Protect the file:

```bash
sudo chown flaskapp:flaskapp /opt/flask-service/.env
sudo chmod 600 /opt/flask-service/.env
```

Do not commit `.env` to Git.

## Automated deployment

Clone the repository:

```bash
git clone https://github.com/liltaya/Flask-service.git
cd Flask-service
```

Create the application user and directory:

```bash
sudo useradd \
  --system \
  --create-home \
  --shell /usr/sbin/nologin \
  flaskapp

sudo mkdir -p /opt/flask-service
```

Copy the project:

```bash
sudo rsync -a \
  --exclude='.git' \
  ./ \
  /opt/flask-service/

sudo chown -R flaskapp:flaskapp /opt/flask-service
```

Run deployment:

```bash
cd /opt/flask-service
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

The deployment script:

1. Installs operating-system dependencies.
2. Creates the Python virtual environment.
3. Installs packages from `requirements.txt`.
4. Copies application and deployment configuration files.
5. Installs the systemd service.
6. Installs and validates the Nginx configuration.
7. Restarts the Flask and Nginx services.
8. Checks the `/health` endpoint.
9. Prints service diagnostics if deployment fails.

## Docker Compose

The API and PostgreSQL can also run in Docker Compose. See DOCKER.md.

## Verification

Check service status:

```bash
sudo systemctl is-active flask-service
sudo systemctl is-active nginx
sudo systemctl is-active postgresql
```

Test the health endpoint through Nginx:

```bash
curl -i http://127.0.0.1/health
```

Expected response:

```json
{
  "status": "ok",
  "database": "connected"
}
```

## CRUD examples

Create an item:

```bash
curl -i -X POST http://127.0.0.1/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo item"}'
```

Get all items:

```bash
curl -i http://127.0.0.1/items
```

Update an item:

```bash
curl -i -X PUT http://127.0.0.1/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated item"}'
```

Delete an item:

```bash
curl -i -X DELETE http://127.0.0.1/items/1
```

## Input validation

The API validates:

- `Content-Type: application/json`
- valid JSON syntax
- JSON object structure
- presence of the `name` field
- string type
- non-empty values
- maximum length of 200 characters

## Error handling

The application returns JSON errors for:

| Status | Meaning |
| --- | --- |
| 400 | Bad Request |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 415 | Unsupported Media Type |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

Nginx returns `502 Bad Gateway` when the Flask upstream is unavailable.

## Log analyzer

`tools/log_analyzer.py` reads Nginx or Apache access logs (common or combined format) and reports error rates, malformed lines, top IPs, and suspicious requests such as path traversal, SQL injection attempts and scanners.

```bash
python tools/log_analyzer.py /var/log/nginx/access.log
python tools/log_analyzer.py access.log --format json --output report.json
python tools/log_analyzer.py access.log --format csv --top 20
cat access.log | python tools/log_analyzer.py -
```

| Option | Description |
| --- | --- |
| `log_file` | Path to the access log, or `-` to read from stdin |
| `--top N` | Number of top IPs and suspicious samples to show (default 10) |
| `--format` | `text`, `json` or `csv` (default `text`) |
| `--output PATH` | Write the report to a file instead of stdout |

Benchmark on generated data (1,000,000 rows by default):

```bash
python benchmarks/benchmark_log_analyzer.py --rows 1000000
```

## Tests and CI

```bash
pip install -r requirements-dev.txt
pytest -v
```

GitHub Actions runs four jobs on every push and pull request to `main`: Ruff (lint and format), mypy, pytest against PostgreSQL, and coverage.

## Logs

Application service logs:

```bash
sudo journalctl -u flask-service -n 100 --no-pager
```

Nginx error logs:

```bash
sudo tail -n 100 /var/log/nginx/error.log
```

## Security

- Database credentials are stored in `.env`, which is excluded through `.gitignore`.
- Flask listens behind Nginx.
- Debug mode is disabled.
- The application runs as the unprivileged `flaskapp` user.
- Port 5000 should not be exposed publicly.

## Author

Taisiia (Taya) Mamenko · Portfolio · GitHub

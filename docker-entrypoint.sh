#!/bin/sh
set -eu

python - <<'PY'
from app import app, db

with app.app_context():
    db.create_all()

print("Database schema is ready.", flush=True)
PY

exec "$@"

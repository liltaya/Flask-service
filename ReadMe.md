# Flask Service
- `/health` 
- `/metrics` xs

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py

The application uses PostgreSQL.

Database name:

```text
flask_service

rom flask import Flask

app = Flask(__name__)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return "metrics"


@app.post("/items")
def create_item():
    return {"message": "item created"}


@app.get("/items")
def get_items():
    return {"items": []}


@app.get("/items/<int:item_id>")
def get_item(item_id):
    return {"id": item_id}


if __name__ == "__main__":
    app.run(debug=True)

/////Tests
Install dependencies:

pip install -r requirements.txt

Run tests:

pytest

Run tests with coverage:

pytest --cov=app --cov-report=term-missing

Create an HTML coverage report:

pytest --cov=app --cov-report=html
open htmlcov/index.html

Flask Service

Simple REST API built with Flask, SQLAlchemy and PostgreSQL.

The service provides CRUD operations for items, application health checks and Prometheus metrics.

Features
Create items
Get all items
Get one item by ID
Update items
Delete items
Validate request data
Check application and database health
Expose Prometheus metrics
Run automated API tests
Measure code coverage
Technology Stack
Python
Flask
Flask-SQLAlchemy
PostgreSQL
SQLite for tests
Pytest
Pytest-cov
Prometheus Client
Project Structure
flask-service/
├── app.py
├── tests/
│   ├── conftest.py
│   └── test_api.py
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md


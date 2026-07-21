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
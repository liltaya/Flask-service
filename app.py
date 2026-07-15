from flask import Flask, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql+psycopg://localhost/flask_service"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

request_counter = Counter(
    "application_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)


class Item(db.Model):
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
        }


@app.after_request
def record_request_metrics(response):
    request_counter.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code,
    ).inc()

    return response


@app.get("/")
def home():
    return jsonify(
        {
            "message": "Flask application is running",
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "create_item": "POST /items",
                "get_items": "GET /items",
                "get_item": "GET /items/<id>",
            },
        }
    )


@app.get("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))

        return jsonify(
            {
                "status": "ok",
                "database": "connected",
            }
        ), 200

    except SQLAlchemyError:
        return jsonify(
            {
                "status": "error",
                "database": "disconnected",
            }
        ), 503


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
    )


@app.post("/items")
def create_item():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify(
            {
                "error": "Request body must contain valid JSON"
            }
        ), 400

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        return jsonify(
            {
                "error": "Field 'name' is required and must be a non-empty string"
            }
        ), 400

    if len(name.strip()) > 200:
        return jsonify(
            {
                "error": "Field 'name' cannot be longer than 200 characters"
            }
        ), 400

    try:
        item = Item(name=name.strip())

        db.session.add(item)
        db.session.commit()

        return jsonify(item.to_dict()), 201

    except SQLAlchemyError:
        db.session.rollback()

        app.logger.exception("Could not create item")

        return jsonify(
            {
                "error": "Database error"
            }
        ), 500


@app.get("/items")
def get_items():
    try:
        items = db.session.execute(
            db.select(Item).order_by(Item.id)
        ).scalars().all()

        return jsonify(
            {
                "items": [item.to_dict() for item in items],
                "count": len(items),
            }
        ), 200

    except SQLAlchemyError:
        app.logger.exception("Could not get items")

        return jsonify(
            {
                "error": "Database error"
            }
        ), 500


@app.get("/items/<int:item_id>")
def get_item(item_id):
    try:
        item = db.session.get(Item, item_id)

        if item is None:
            return jsonify(
                {
                    "error": "Item not found"
                }
            ), 404

        return jsonify(item.to_dict()), 200

    except SQLAlchemyError:
        app.logger.exception("Could not get item")

        return jsonify(
            {
                "error": "Database error"
            }
        ), 500


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify(
        {
            "error": "Endpoint not found"
        }
    ), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    return jsonify(
        {
            "error": "Method not allowed"
        }
    ), 405


@app.errorhandler(500)
def handle_internal_error(error):
    db.session.rollback()

    return jsonify(
        {
            "error": "Internal server error"
        }
    ), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
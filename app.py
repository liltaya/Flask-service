from flask import Flask, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

app = Flask(__name__)

request_counter = Counter(
    "application_requests_total",
    "Total number of requests",
)


@app.get("/")
def home():
    request_counter.inc()
    return jsonify({"message": "Flask application is running"})


@app.get("/health")
def health():
    request_counter.inc()
    return jsonify({"status": "ok"})


@app.get("/metrics")
def metrics():
    request_counter.inc()
    return Response(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
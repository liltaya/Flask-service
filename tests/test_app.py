import pytest

from app import app, db


@pytest.fixture()
def client():
    app.config.update(
        TESTING=True,
    )

    with app.app_context():
        db.create_all()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_json()["message"] == "Flask API is running"


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "database": "connected",
    }


def test_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"application_up" in response.data


def test_create_and_get_item(client):
    create_response = client.post(
        "/items",
        json={"name": "CI item"},
    )

    assert create_response.status_code == 201
    item_id = create_response.get_json()["id"]

    get_response = client.get(f"/items/{item_id}")

    assert get_response.status_code == 200
    assert get_response.get_json()["name"] == "CI item"


def test_create_item_without_json(client):
    response = client.post(
        "/items",
        data="not-json",
    )

    assert response.status_code == 415


def test_create_item_with_empty_name(client):
    response = client.post(
        "/items",
        json={"name": "   "},
    )

    assert response.status_code == 400


def test_unknown_endpoint(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404

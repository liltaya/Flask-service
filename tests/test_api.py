def create_item(client, name="Apple"):
    return client.post(
        "/items",
        json={"name": name},
    )


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_get_empty_items(client):
    response = client.get("/items")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 0
    assert data["items"] == []


def test_create_item(client):
    response = create_item(client, "Apple")

    assert response.status_code == 201

    data = response.get_json()

    assert data["id"] == 1
    assert data["name"] == "Apple"


def test_get_all_items(client):
    create_item(client, "Apple")
    create_item(client, "Banana")

    response = client.get("/items")

    assert response.status_code == 200

    data = response.get_json()

    assert data["count"] == 2
    assert data["items"][0]["name"] == "Apple"
    assert data["items"][1]["name"] == "Banana"


def test_get_one_item(client):
    create_response = create_item(client, "Apple")
    item_id = create_response.get_json()["id"]

    response = client.get(f"/items/{item_id}")

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == item_id
    assert data["name"] == "Apple"


def test_get_missing_item(client):
    response = client.get("/items/999")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Item not found",
    }


def test_update_item(client):
    create_response = create_item(client, "Apple")
    item_id = create_response.get_json()["id"]

    response = client.put(
        f"/items/{item_id}",
        json={"name": "Green Apple"},
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["id"] == item_id
    assert data["name"] == "Green Apple"


def test_update_missing_item(client):
    response = client.put(
        "/items/999",
        json={"name": "Green Apple"},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Item not found",
    }


def test_delete_item(client):
    create_response = create_item(client, "Apple")
    item_id = create_response.get_json()["id"]

    delete_response = client.delete(f"/items/{item_id}")

    assert delete_response.status_code == 200
    assert delete_response.get_json()["message"] == "Item deleted"

    get_response = client.get(f"/items/{item_id}")

    assert get_response.status_code == 404


def test_delete_missing_item(client):
    response = client.delete("/items/999")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Item not found",
    }


def test_create_without_json(client):
    response = client.post(
        "/items",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Request body must contain valid JSON",
    }


def test_create_without_name(client):
    response = client.post(
        "/items",
        json={},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'name' is required",
    }


def test_create_with_non_string_name(client):
    response = client.post(
        "/items",
        json={"name": 123},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'name' must be a string",
    }


def test_create_with_empty_name(client):
    response = client.post(
        "/items",
        json={"name": " "},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'name' cannot be empty",
    }


def test_create_with_long_name(client):
    response = client.post(
        "/items",
        json={"name": "A" * 201},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'name' cannot be longer than 200 characters",
    }


def test_update_validation(client):
    create_response = create_item(client, "Apple")
    item_id = create_response.get_json()["id"]

    response = client.put(
        f"/items/{item_id}",
        json={"name": ""},
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "Field 'name' cannot be empty",
    }


def test_unknown_endpoint(client):
    response = client.get("/unknown")

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Endpoint not found",
    }


def test_method_not_allowed(client):
    response = client.post("/health")

    assert response.status_code == 405
    assert response.get_json() == {
        "error": "Method not allowed",
    }


def test_metrics(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert b"application_requests_total" in response.data
    
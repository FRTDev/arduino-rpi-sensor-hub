import base64


def basic_auth(username="tester", password="test-password"):
    value = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {value}"}


def test_data_ingestion_requires_gateway_key(client):
    response = client.post(
        "/api/data",
        json={"arduino_id": "arduino1", "valeur": "42"},
    )
    assert response.status_code == 401


def test_data_ingestion_accepts_valid_gateway_key(client):
    response = client.post(
        "/api/data",
        json={"arduino_id": "arduino1", "valeur": "42"},
        headers={"X-API-Key": "test-gateway-key"},
    )
    assert response.status_code == 201


def test_command_rejects_invalid_value(client):
    response = client.post(
        "/api/consignes",
        json={"arduino_id": "arduino1", "valeur": "INVALID"},
        headers=basic_auth(),
    )
    assert response.status_code == 400


def test_history_reset_requires_dashboard_auth(client):
    response = client.post("/reset-historique")
    assert response.status_code == 401


def test_history_reset_accepts_dashboard_auth(client):
    response = client.post(
        "/reset-historique",
        headers=basic_auth(),
    )
    assert response.status_code == 302

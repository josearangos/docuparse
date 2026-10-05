def test_healthy(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "service": "docuparse", "version": "0.1.0"}


def test_not_ready(client, engine):
    engine.ready = False
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"

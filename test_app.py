import pytest

import app as app_module


@pytest.fixture
def client(tmp_path):
    app_module.app.config["DATABASE"] = str(tmp_path / "test.db")
    app_module.init_db()
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def test_shorten_and_redirect(client):
    res = client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    code = res.get_json()["code"]

    redirect_res = client.get(f"/{code}")
    assert redirect_res.status_code == 302
    assert redirect_res.headers["Location"] == "https://example.com"


def test_invalid_url_rejected(client):
    res = client.post("/api/shorten", json={"url": "not-a-url"})
    assert res.status_code == 400


def test_click_counter(client):
    code = client.post("/api/shorten", json={"url": "https://example.com"}).get_json()["code"]
    client.get(f"/{code}")
    client.get(f"/{code}")
    assert client.get(f"/api/stats/{code}").get_json()["clicks"] == 2


def test_unknown_code_404(client):
    assert client.get("/nope123").status_code == 404

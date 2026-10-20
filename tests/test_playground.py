import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from nullmark.models import CausalModel
from nullmark.playground.app import create_app
from nullmark.playground.service import Playground, PlaygroundSettings


@pytest.fixture
def client():
    return TestClient(create_app(), base_url="http://127.0.0.1")


def test_fixed_routes_and_local_boundary(client):
    page = client.get("/")
    assert page.status_code == 200 and "NullMark" in page.text
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    for path in ("/private/secrets.json", "/assets/secrets.json", "/assets/../service.py"):
        assert client.get(path).status_code == 404
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400
    assert (
        client.post("/api/key", json={}, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert client.post("/api/key", content="{}").status_code == 415
    assert client.post("/api/key", json={}).status_code == 200
    assert (
        client.post(
            "/api/key", content="x" * 100001, headers={"Content-Type": "application/json"}
        ).status_code
        == 413
    )


@pytest.mark.parametrize("name", ["none", "kgw", "synthid"])
def test_offline_generation_routes(client, name):
    response = client.post(
        "/api/generate", json={"prompt": "word1 word2", "scheme": name, "max_new_tokens": 32}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["marked"]["token_count"] == 32
    assert bool(data["plain"]) == (name != "none")
    assert "hashing_key" not in response.text and "master" not in response.text


@pytest.mark.parametrize(
    "bad",
    [
        {"seed": -1},
        {"depth": 1},
        {"scheme": "skd"},
        {"prompt": ""},
        {"kgw": {"bias": 99}},
        {"model": "arbitrary"},
    ],
)
def test_invalid_settings_are_controlled(client, bad):
    response = client.post("/api/generate", json={"prompt": "word1", **bad})
    assert response.status_code == 422
    assert set(response.json()) == {"error"}


@pytest.mark.parametrize("error", [RuntimeError, ValueError, OSError])
def test_failure_sanitized(client, monkeypatch, error):
    def fail(self, settings):
        raise error("PRIVATE SECRET SHOULD NOT LEAK")

    monkeypatch.setattr(Playground, "generate", fail)
    response = client.post("/api/generate", json={"prompt": "word1"})
    assert response.status_code == 400 and "PRIVATE" not in response.text


def test_prompt_context_limit(client, monkeypatch):
    original = CausalModel.__init__

    def small_context(self, config):
        original(self, config)
        self.model.config.max_position_embeddings = 32

    monkeypatch.setattr(CausalModel, "__init__", small_context)
    response = client.post("/api/generate", json={"prompt": "word1 " * 20, "max_new_tokens": 16})
    assert response.status_code == 400
    assert "shorter prompt" in response.text


def test_busy_requests(client, monkeypatch):
    def busy(self, settings):
        # Reentrant request while the first request holds the generation lock.
        assert client.post("/api/key", json={}).status_code == 409
        assert client.post("/api/generate", json={"prompt": "word1"}).status_code == 409
        return {"status": "checked"}

    monkeypatch.setattr(Playground, "generate", busy)
    assert client.post("/api/generate", json={"prompt": "word1"}).status_code == 200


def test_cache_and_fresh_key():
    service = Playground()
    settings = PlaygroundSettings(prompt="word1", max_new_tokens=16)
    first = service.generate(settings)
    model = next(iter(service._models.values()))
    replay = service.generate(settings)
    assert model is next(iter(service._models.values()))
    assert first["key_ref"] == replay["key_ref"]
    assert first["marked"]["text"] == replay["marked"]["text"]
    service.fresh_key()
    fresh = service.generate(settings)
    assert first["key_ref"] != fresh["key_ref"]
    assert service._keys.master.hex() not in json.dumps(fresh)

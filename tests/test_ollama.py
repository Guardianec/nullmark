import hashlib
import io
import json
import subprocess

import pytest

from nullmark.models import ollama


def model_row(**extra):
    return {
        "name": "qwen-local:9b",
        "digest": "a" * 64,
        "size": 123,
        "details": {"format": "gguf", "quantization_level": "Q4_K_M", "parameter_size": "9B"},
        **extra,
    }


def test_discovery_local_and_cloud(monkeypatch):
    monkeypatch.setattr(
        ollama,
        "local_request",
        lambda endpoint: {
            "models": [
                model_row(),
                model_row(name="remote:cloud", remote_host="https://cloud.example"),
            ]
        },
    )
    models = ollama.list_models()
    assert models[0].supported and models[0].quantization == "Q4_K_M"
    assert not models[1].supported
    with pytest.raises(ollama.LocalModelError, match="cloud"):
        ollama.resolve_model("remote:cloud")


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"models": None},
        {"models": [None]},
        {"models": [model_row(details=[])]},
        {"models": [model_row(size=-1)]},
    ],
)
def test_malformed_discovery(monkeypatch, response):
    monkeypatch.setattr(ollama, "local_request", lambda endpoint: response)
    with pytest.raises(ollama.LocalModelError):
        ollama.list_models()


def test_only_loopback_and_no_proxy_or_redirect(monkeypatch):
    seen = []

    class Opener:
        def open(self, request, timeout):
            seen.append(request.full_url)
            assert request.full_url == "http://127.0.0.1:11434/api/tags"
            assert timeout == 10
            return io.BytesIO(b'{"models":[]}')

    def build(*handlers):
        assert handlers[0].proxies == {}
        assert isinstance(handlers[1], ollama.NoRedirect)
        return Opener()

    monkeypatch.setattr(ollama.urllib.request, "build_opener", build)
    assert ollama.local_request("/api/tags") == {"models": []}
    assert len(seen) == 1
    with pytest.raises(ollama.LocalModelError, match="redirect"):
        ollama.NoRedirect().redirect_request(None, None, 302, "", {}, "https://cloud.example")


def test_offline_discovery(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("PRIVATE local details")

    monkeypatch.setattr(ollama.urllib.request.OpenerDirector, "open", fail)
    with pytest.raises(ollama.LocalModelError, match="Start Ollama") as error:
        ollama.local_request("/api/tags")
    assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize("parent_manifest", [False, True])
def test_blob_resolution_spaces_projector_and_digest(tmp_path, monkeypatch, parent_manifest):
    root = tmp_path / "models with spaces"
    blobs = root / "blobs"
    blobs.mkdir(parents=True)
    raw = b"GGUF language weights fixture"
    digest = hashlib.sha256(raw).hexdigest()
    blob = blobs / ("sha256-" + digest)
    blob.write_bytes(raw)
    projector = blobs / ("sha256-" + "b" * 64)
    projector.write_bytes(b"GGUF projector")
    layers = [
        {"mediaType": "application/vnd.ollama.image.model", "digest": "sha256:" + digest},
        {"mediaType": "application/vnd.ollama.image.projector", "digest": "sha256:" + "b" * 64},
    ]
    if parent_manifest:
        layers.append(
            {
                "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                "digest": "sha256:" + "a" * 64,
            }
        )
    manifest = json.dumps({"layers": layers}).encode()
    manifests = root / "manifests"
    manifests.mkdir()
    (manifests / "tag").write_bytes(manifest)
    tag_digest = "a" * 64 if parent_manifest else hashlib.sha256(manifest).hexdigest()
    monkeypatch.setattr(
        ollama, "local_request", lambda endpoint: {"models": [model_row(digest=tag_digest)]}
    )
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "ollama.exe")

    def show(args, **kwargs):
        assert args == ["ollama.exe", "show", "--modelfile", "qwen-local:9b"]
        assert kwargs["env"]["OLLAMA_HOST"] == ollama.BASE
        return subprocess.CompletedProcess(args, 0, stdout=f'FROM {projector}\nFROM "{blob}"\n')

    monkeypatch.setattr(ollama.subprocess, "run", show)
    local = ollama.resolve_model("qwen-local:9b", expected_digest=digest)
    assert local.path == blob.resolve() and local.blob_sha256 == digest
    assert str(root) not in json.dumps(local.public_metadata())
    with pytest.raises(ollama.LocalModelError, match="digest changed"):
        ollama.resolve_model("qwen-local:9b", expected_digest="c" * 64)


@pytest.mark.parametrize("modelfile", ["", "FROM remote:cloud", "FROM missing model.gguf"])
def test_missing_blob_or_malformed_modelfile(monkeypatch, modelfile):
    monkeypatch.setattr(ollama, "local_request", lambda endpoint: {"models": [model_row()]})
    monkeypatch.setattr(ollama.shutil, "which", lambda name: "ollama.exe")
    monkeypatch.setattr(
        ollama.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=modelfile),
    )
    with pytest.raises(ollama.LocalModelError, match="no readable local GGUF"):
        ollama.resolve_model("qwen-local:9b")

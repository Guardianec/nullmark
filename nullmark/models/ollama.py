"""Local-only Ollama discovery; never generation, pulling or cloud fallback."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from nullmark.common.errors import LocalModelError

BASE = "http://127.0.0.1:11434"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocalModelError("Ollama discovery refused a redirect; only localhost is supported.")


def local_request(endpoint: str, body: dict | None = None) -> dict:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(
        BASE + endpoint,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with opener.open(request, timeout=10) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise LocalModelError("Ollama returned oversized discovery metadata.")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError
        return result
    except LocalModelError:
        raise
    except (OSError, ValueError, urllib.error.URLError):
        raise LocalModelError(
            "Ollama is not reachable at localhost:11434 or returned invalid metadata. "
            "Start Ollama and refresh."
        ) from None


@dataclass(frozen=True)
class InstalledModel:
    name: str
    digest: str
    size: int
    quantization: str
    parameter_size: str
    supported: bool
    status: str


@dataclass(frozen=True)
class LocalGGUF:
    model: InstalledModel
    blob_sha256: str
    path: Path = field(repr=False)

    def public_metadata(self) -> dict:
        return {**asdict(self.model), "blob_sha256": self.blob_sha256}


def list_models() -> list[InstalledModel]:
    rows = local_request("/api/tags").get("models")
    if not isinstance(rows, list):
        raise LocalModelError("Ollama returned an invalid model list.")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            raise LocalModelError("Ollama returned invalid model metadata.")
        details = row.get("details", {})
        if not isinstance(details, dict):
            raise LocalModelError("Ollama returned invalid model details.")
        name = row.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,255}", name
        ):
            continue
        supported = details.get("format") == "gguf" and not row.get("remote_host")
        if not isinstance(row.get("size", 0), int) or row.get("size", 0) < 0:
            raise LocalModelError("Ollama returned an invalid model size.")
        result.append(
            InstalledModel(
                name,
                row.get("digest", ""),
                int(row.get("size", 0)),
                details.get("quantization_level", "unknown"),
                details.get("parameter_size", "unknown"),
                supported,
                "Local GGUF; load capability must be checked"
                if supported
                else "Unsupported: local GGUF weights required (no cloud fallback)",
            )
        )
    return result


def resolve_model(name: str, *, expected_digest: str | None = None) -> LocalGGUF:
    model = next((m for m in list_models() if m.name == name), None)
    if model is None or not model.supported:
        raise LocalModelError(
            "Select an installed, local GGUF model; cloud models are unsupported."
        )
    executable = shutil.which("ollama")
    if not executable:
        raise LocalModelError("Ollama CLI is missing from PATH; needed to resolve the local GGUF.")
    try:
        run = subprocess.run(
            [executable, "show", "--modelfile", name],
            capture_output=True,
            encoding="utf-8",
            timeout=20,
            check=True,
            env={**os.environ, "OLLAMA_HOST": BASE},
        )
        if re.search(r"^\s*ADAPTER\b", run.stdout, re.MULTILINE):
            raise LocalModelError(
                "Ollama adapter layers are unsupported; select a self-contained GGUF."
            )
        candidates = [
            Path(p.strip().strip('"')).resolve()
            for p in re.findall(r"^FROM (.+)$", run.stdout, re.MULTILINE)
        ]
        candidates = [p for p in candidates if p.is_file()]
    except (OSError, subprocess.SubprocessError):
        raise LocalModelError(
            "Ollama could not resolve the installed model's local Modelfile."
        ) from None
    if not candidates:
        raise LocalModelError(
            "The Modelfile has no readable local GGUF blob; no model was downloaded."
        )
    # Match the content-addressed manifest's language-model layer, excluding vision projectors.
    selected = None
    for root in {p.parent.parent for p in candidates}:
        for manifest in (root / "manifests").rglob("*"):
            if not manifest.is_file() or manifest.stat().st_size > 1_000_000:
                continue
            raw = manifest.read_bytes()
            try:
                layers = json.loads(raw)["layers"]
                # New Ollama releases can retain the original manifest digest as a layer.
                matches = hashlib.sha256(raw).hexdigest() == model.digest or any(
                    layer.get("mediaType") == "application/vnd.docker.distribution.manifest.v2+json"
                    and layer.get("digest") == "sha256:" + model.digest
                    for layer in layers
                )
                if not matches:
                    continue
                digests = [
                    layer["digest"].replace(":", "-")
                    for layer in layers
                    if layer["mediaType"] == "application/vnd.ollama.image.model"
                ]
                if len(digests) != 1:
                    raise LocalModelError(
                        "Only a single self-contained language GGUF is supported."
                    )
            except LocalModelError:
                raise
            except (ValueError, KeyError, TypeError):
                raise LocalModelError("Invalid local Ollama model manifest.") from None
            selected = next((p for p in candidates if p.name in digests), None)
    if selected is None and len(candidates) == 1:
        selected = candidates[0]
    if selected is None:
        raise LocalModelError("Cannot distinguish the language GGUF from auxiliary blobs.")
    with selected.open("rb") as handle:
        if handle.read(4) != b"GGUF":
            raise LocalModelError("The selected local model is not a supported GGUF file.")
    match = re.fullmatch(r"sha256-([0-9a-f]{64})", selected.name)
    if not match:
        raise LocalModelError("The local GGUF lacks an Ollama content-addressed blob identifier.")
    digest = match[1]
    if expected_digest is not None and digest != expected_digest:
        raise LocalModelError(
            "Installed GGUF digest changed; select or pin the intended model again."
        )
    return LocalGGUF(model, digest, selected)

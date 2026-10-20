"""Single-user playground state. Masters stay in memory; no key files are served."""

from dataclasses import asdict
from threading import Lock
from typing import Literal

from pydantic import Field

from nullmark.config import KGWConfig, ModelConfig, StrictConfig, SynthIDConfig
from nullmark.evaluation.inspection import paired_generation
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.models import TextGenerationBackend, load_model
from nullmark.models.ollama import resolve_model
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme

GPT2_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"


class PlaygroundSettings(StrictConfig):
    model: Literal["builtin-tiny", "gpt2", "ollama"] = "builtin-tiny"
    ollama_model: str | None = Field(None, max_length=256)
    ollama_digest: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")
    offload: Literal["auto", "cpu", "gpu"] = "auto"
    context_length: int = Field(2048, ge=128, le=8192)
    scheme: Literal["none", "kgw", "synthid"] = "kgw"
    device: Literal["cpu", "cuda"] = "cpu"
    prompt: str = Field(min_length=1, max_length=16000)
    seed: int = Field(42, ge=0, lt=2**32)
    key_index: int = Field(0, ge=0, le=999)
    max_new_tokens: int = Field(128, ge=16, le=512)
    temperature: float = Field(0.8, gt=0, le=5)
    top_k: int = Field(40, ge=0, le=1000000)
    top_p: float = Field(0.95, gt=0, le=1)
    paired: bool = True
    kgw: KGWConfig = Field(default_factory=KGWConfig)
    synthid: SynthIDConfig = Field(default_factory=SynthIDConfig)


class Playground:
    def __init__(self):
        self._keys = KeyStore.create()
        self._models: dict[tuple, TextGenerationBackend] = {}
        self.lock = Lock()

    def fresh_key(self) -> dict:
        self._keys = KeyStore.create()
        return {"status": "fresh hidden key configuration"}

    def generate(self, settings: PlaygroundSettings) -> dict:
        cache_key = (
            settings.model,
            settings.device,
            settings.ollama_model,
            settings.ollama_digest,
            settings.offload,
            settings.context_length,
        )
        model = self._models.get(cache_key)
        local = None
        if model is None:
            for previous in self._models.values():
                previous.close()
            self._models.clear()
            if settings.model == "ollama":
                local = resolve_model(settings.ollama_model or "")
                if settings.ollama_digest and local.model.digest != settings.ollama_digest:
                    from nullmark.models.ollama import LocalModelError

                    raise LocalModelError("Installed model changed; refresh and select it again.")
        config = ModelConfig(
            name="builtin-tiny" if settings.model == "builtin-tiny" else "openai-community/gpt2",
            revision=None if settings.model == "builtin-tiny" else GPT2_REVISION,
            device=settings.device,
            max_new_tokens=settings.max_new_tokens,
            temperature=settings.temperature,
            top_k=settings.top_k,
            top_p=settings.top_p,
        )
        if settings.model == "ollama":
            # Build from validated local discovery, never a browser-supplied filesystem path.
            config = ModelConfig(
                backend="ollama-gguf",
                name=settings.ollama_model,
                revision=local.blob_sha256 if local else model.settings.revision,
                temperature=settings.temperature,
                top_k=settings.top_k,
                top_p=settings.top_p,
                max_new_tokens=settings.max_new_tokens,
                threads=8,
                context_length=settings.context_length,
                offload=settings.offload,
            )
        if model is None:
            if local:
                from nullmark.models.gguf import GGUFBackend

                model = GGUFBackend(config, local)
            else:
                model = load_model(config)
            self._models[cache_key] = model
        model.settings = config
        scheme = None
        if settings.scheme != "none":
            secret = self._keys.derive(settings.scheme, settings.key_index, settings.synthid.depth)
            scheme = (
                KGWScheme(model, settings.kgw, secret)
                if settings.scheme == "kgw"
                else SynthIDScheme(model, settings.synthid, secret)
            )
        result = asdict(
            paired_generation(
                model,
                scheme,
                settings.prompt,
                seed=settings.seed,
                paired=settings.paired,
            )
        )
        result["key_ref"] = (
            key_reference(self._keys, settings.scheme, settings.key_index) if scheme else None
        )
        result["model"] = model.metadata()
        return result

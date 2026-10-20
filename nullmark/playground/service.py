"""Single-user playground state. Masters stay in memory; no key files are served."""

from dataclasses import asdict
from threading import Lock
from typing import Literal

from pydantic import Field

from nullmark.config import KGWConfig, ModelConfig, StrictConfig, SynthIDConfig
from nullmark.evaluation.inspection import paired_generation
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.models import CausalModel
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme

GPT2_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"


class PlaygroundSettings(StrictConfig):
    model: Literal["builtin-tiny", "gpt2"] = "builtin-tiny"
    scheme: Literal["none", "kgw", "synthid"] = "kgw"
    device: Literal["cpu", "cuda"] = "cpu"
    prompt: str = Field(min_length=1, max_length=16000)
    seed: int = Field(42, ge=0, lt=2**32)
    key_index: int = Field(0, ge=0, le=999)
    max_new_tokens: int = Field(128, ge=16, le=512)
    temperature: float = Field(1.0, gt=0, le=5)
    paired: bool = True
    kgw: KGWConfig = Field(default_factory=KGWConfig)
    synthid: SynthIDConfig = Field(default_factory=SynthIDConfig)


class Playground:
    def __init__(self):
        self._keys = KeyStore.create()
        self._models: dict[tuple[str, str], CausalModel] = {}
        self.lock = Lock()

    def fresh_key(self) -> dict:
        self._keys = KeyStore.create()
        return {"status": "fresh hidden key configuration"}

    def generate(self, settings: PlaygroundSettings) -> dict:
        config = ModelConfig(
            name="builtin-tiny" if settings.model == "builtin-tiny" else "openai-community/gpt2",
            revision=None if settings.model == "builtin-tiny" else GPT2_REVISION,
            device=settings.device,
            max_new_tokens=settings.max_new_tokens,
            temperature=settings.temperature,
        )
        cache_key = (settings.model, settings.device)
        if cache_key not in self._models:
            # Bound memory: keep only the active model/device, reused across generations.
            self._models.clear()
            self._models[cache_key] = CausalModel(config)
        model = self._models[cache_key]
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

"""The inference surface shared by generation, watermarking and trusted inspection."""

from typing import Any, Protocol

from nullmark.config import ModelConfig
from nullmark.models.causal import CausalModel, Generation


class TextGenerationBackend(Protocol):
    settings: ModelConfig
    vocab_size: int
    detector_config: Any
    watermark_device: str
    eos_token_ids: frozenset[int]
    special_token_ids: frozenset[int]

    def encode(self, text: str) -> list[int]: ...
    def encode_prompt(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...
    def metadata(self) -> dict: ...
    def generate(self, prompt: str, *, seed: int, watermark: Any = None) -> Generation: ...
    def close(self) -> None: ...


def load_model(config: ModelConfig) -> TextGenerationBackend:
    if config.backend == "ollama-gguf":
        from nullmark.models.gguf import GGUFBackend
        from nullmark.models.ollama import resolve_model

        return GGUFBackend(config, resolve_model(config.name, expected_digest=config.revision))
    return CausalModel(config)

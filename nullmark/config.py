"""Validated public configuration. Secrets never belong in this schema."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


class ModelConfig(StrictConfig):
    name: str = "builtin-tiny"
    revision: str | None = None
    device: Literal["cpu", "cuda"] = "cpu"
    max_new_tokens: int = Field(128, ge=16, le=4096)
    temperature: float = Field(1.0, gt=0, le=5)
    threads: int = Field(1, ge=1, le=64)

    @model_validator(mode="after")
    def pinned_revision(self):
        if self.name != "builtin-tiny" and (
            self.revision is None
            or len(self.revision) != 40
            or any(c not in "0123456789abcdef" for c in self.revision)
        ):
            raise ValueError(
                "pretrained models require a full lowercase 40-character commit revision"
            )
        return self


class SynthIDConfig(StrictConfig):
    ngram_len: int = Field(5, ge=2, le=16)
    depth: int = Field(10, ge=1, le=30)
    context_history_size: int = Field(1024, ge=16, le=65536)
    sampling_table_size: int = Field(65536, ge=256, le=1048576)
    threshold: float = Field(0.60, gt=0.5, lt=1)


class KGWConfig(StrictConfig):
    greenlist_ratio: float = Field(0.25, gt=0, lt=1)
    bias: float = Field(2.5, gt=0, le=10)
    context_width: int = Field(1, ge=1, le=8)
    threshold: float = Field(3.0, gt=0)
    ignore_repeated_ngrams: bool = True


class DatasetConfig(StrictConfig):
    source: Literal["builtin-v1", "jsonl"] = "builtin-v1"
    path: str | None = None
    sample_count: int = Field(2, ge=1)

    @model_validator(mode="after")
    def valid_source(self):
        if (self.source == "jsonl") != (self.path is not None):
            raise ValueError("path is required only for source=jsonl")
        return self


class ExperimentConfig(StrictConfig):
    name: str = Field("001_watermark_reproducibility", pattern=r"^[a-zA-Z0-9_-]+$")
    seed: int = Field(42, ge=0, lt=2**32)
    purpose: Literal["smoke", "benchmark"] = "smoke"
    random_keys: int = Field(2, ge=1, le=1000)
    model: ModelConfig = Field(default_factory=ModelConfig)
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    synthid: SynthIDConfig = Field(default_factory=SynthIDConfig)
    kgw: KGWConfig = Field(default_factory=KGWConfig)

    @model_validator(mode="after")
    def enough_context(self):
        if self.model.max_new_tokens <= max(self.synthid.ngram_len, self.kgw.context_width):
            raise ValueError("max_new_tokens must exceed watermark context length")
        if self.purpose == "benchmark" and self.model.name == "builtin-tiny":
            raise ValueError("builtin-tiny is an untrained smoke model, not a benchmark model")
        return self


def load_config(path: Path) -> ExperimentConfig:
    return ExperimentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))

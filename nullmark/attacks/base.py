"""The public, detector-blind transformation interface."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AttackInput:
    sample_id: str
    prompt: str
    text: str


@dataclass(frozen=True)
class AttackOutput:
    text: str
    attack: str
    version: str
    seed: int
    requested_budget: float | None
    input_sha256: str
    model_digest: str
    sampling: dict
    template_version: str
    actual_word_edits: int
    actual_token_edits: int
    runtime_seconds: float
    warnings: list[str] = field(default_factory=list)
    token_metric: str = "regex lexical tokens; trusted evaluator reports generation-model edits"


class TextTransform(Protocol):
    def transform(self, sample: AttackInput, *, seed: int) -> AttackOutput: ...

"""The only information passed to a future blind text transformation."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AttackInput:
    sample_id: str
    prompt: str
    text: str


class TextTransform(Protocol):
    def transform(self, sample: AttackInput, *, seed: int) -> str: ...

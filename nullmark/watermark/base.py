from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from nullmark.models import Generation, TextGenerationBackend


@dataclass(frozen=True)
class DetectionResult:
    score: float | None
    prediction: bool | None
    threshold: float
    statistic: str
    tokens_scored: int
    p_value: float | None = None
    status: str = "ok"
    decision_scope: str = "legacy_demo"

    @property
    def state(self) -> str:
        if self.prediction is None or self.decision_scope != "calibrated":
            return "INSUFFICIENT EVIDENCE"
        return "DETECTED" if self.prediction else "NOT DETECTED"

    def to_dict(self) -> dict:
        return asdict(self)


class WatermarkScheme(ABC):
    @abstractmethod
    def generation_config(self) -> Any: ...

    @abstractmethod
    def detect(self, text: str) -> DetectionResult: ...

    @abstractmethod
    def score_ids(self, ids: list[int]) -> DetectionResult: ...

    @abstractmethod
    def metadata(self) -> dict: ...

    def generate(self, model: TextGenerationBackend, prompt: str, *, seed: int) -> Generation:
        return model.generate(prompt, seed=seed, watermark=self.generation_config())

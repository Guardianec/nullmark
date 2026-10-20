"""Transformers' KGW-style lefthash processor and repeated-ngram-aware detector."""

from math import erfc, sqrt

import torch
from transformers import WatermarkDetector, WatermarkingConfig

from nullmark.config import KGWConfig
from nullmark.models import TextGenerationBackend
from nullmark.watermark.base import DetectionResult, WatermarkScheme


class KGWScheme(WatermarkScheme):
    def __init__(self, model: TextGenerationBackend, config: KGWConfig, secret: dict):
        self.model = model
        self.config = config
        self._secret = secret
        green_count = int(model.vocab_size * config.greenlist_ratio)
        if green_count < 1 or green_count >= model.vocab_size:
            raise ValueError("greenlist_ratio produces an empty or full vocabulary partition")

    def generation_config(self) -> WatermarkingConfig:
        return WatermarkingConfig(
            greenlist_ratio=self.config.greenlist_ratio,
            bias=self.config.bias,
            hashing_key=self._secret["hashing_key"],
            seeding_scheme="lefthash",
            context_width=self.config.context_width,
        )

    @torch.inference_mode()
    def detect(self, text: str) -> DetectionResult:
        return self.score_ids(self.model.encode(text))

    @torch.inference_mode()
    def score_ids(self, ids: list[int]) -> DetectionResult:
        cfg = self.config
        end = next(
            (i for i, token in enumerate(ids) if token in self.model.eos_token_ids), len(ids)
        )
        ids = ids[:end]
        # HF strips an initial BOS; account for it in the insufficient-text check.
        if ids and ids[0] == self.model.detector_config.bos_token_id:
            ids = ids[1:]
        if len(ids) <= cfg.context_width:
            return DetectionResult(
                None, None, cfg.threshold, "z_score", 0, status="insufficient_text"
            )
        detector = self.detector()
        tensor = torch.tensor([ids], dtype=torch.long, device=self.model.watermark_device)
        result = detector(tensor, z_threshold=cfg.threshold, return_dict=True)
        score = float(result.z_score[0])
        # Use the standard normal survival function, rather than HF's approximate p-value.
        return DetectionResult(
            score,
            bool(result.prediction[0]),
            cfg.threshold,
            "z_score",
            int(result.num_tokens_scored[0]),
            erfc(score / sqrt(2)) / 2,
        )

    def detector(self) -> WatermarkDetector:
        return WatermarkDetector(
            model_config=self.model.detector_config,
            device=self.model.watermark_device,
            watermarking_config=self.generation_config(),
            ignore_repeated_ngrams=self.config.ignore_repeated_ngrams,
        )

    def metadata(self) -> dict:
        return {
            "scheme": "kgw",
            "implementation": "transformers.WatermarkingConfig",
            "detector": "transformers.WatermarkDetector",
            "seeding_scheme": "lefthash",
            "p_value_assumption": "normal approximation, not empirically calibrated",
            **self.config.model_dump(),
        }

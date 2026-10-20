"""HF SynthID generation and reference raw/weighted mean scoring."""

import torch
from transformers import SynthIDTextWatermarkingConfig

from nullmark.config import SynthIDConfig
from nullmark.models import TextGenerationBackend
from nullmark.watermark.base import DetectionResult, WatermarkScheme


def mean_score(values: torch.Tensor, mask: torch.Tensor, statistic: str) -> float:
    """Adapted from google-deepmind/synthid-text detector_mean.py (Apache-2.0).

    Reference default: descending linear layer weights 10..1, normalized by
    their sum. Masking and g-values remain those of the pinned HF processor.
    """
    selected = values[mask].double()
    if statistic == "raw_mean":
        return float(values[mask].float().mean().item())
    if statistic != "weighted_mean":
        raise ValueError("unknown SynthID statistic")
    weights = torch.linspace(10, 1, values.shape[-1], dtype=torch.float64, device=values.device)
    return float(((selected * weights).sum(-1) / weights.sum()).mean().item())


class SynthIDScheme(WatermarkScheme):
    def __init__(self, model: TextGenerationBackend, config: SynthIDConfig, secret: dict):
        if len(secret.get("keys", [])) != config.depth:
            raise ValueError("SynthID secret depth does not match configuration")
        self.model = model
        self.config = config
        self._secret = secret

    def generation_config(self) -> SynthIDTextWatermarkingConfig:
        return SynthIDTextWatermarkingConfig(
            ngram_len=self.config.ngram_len,
            keys=self._secret["keys"],
            sampling_table_seed=self._secret["sampling_table_seed"],
            sampling_table_size=self.config.sampling_table_size,
            context_history_size=self.config.context_history_size,
            skip_first_ngram_calls=True,
        )

    @torch.inference_mode()
    def detect(self, text: str) -> DetectionResult:
        return self.score_ids(self.model.encode(text))

    @torch.inference_mode()
    def score_ids(self, ids: list[int]) -> DetectionResult:
        cfg = self.config
        if len(ids) < cfg.ngram_len:
            return DetectionResult(
                None, None, cfg.threshold, cfg.statistic, 0, status="insufficient_text"
            )
        values, mask = self.scoring_data(ids)
        count = int(mask.sum().item())
        if count == 0:
            return DetectionResult(
                None, None, cfg.threshold, cfg.statistic, 0, status="insufficient_text"
            )
        # Reference mean statistic: sum of unmasked g-values / (depth * unmasked contexts).
        score = mean_score(values, mask, cfg.statistic)
        return DetectionResult(score, score > cfg.threshold, cfg.threshold, cfg.statistic, count)

    def scoring_data(self, ids: list[int]) -> tuple[torch.Tensor, torch.Tensor]:
        processor = self.generation_config().construct_processor(
            self.model.vocab_size,
            self.model.watermark_device,
        )
        tensor = torch.tensor([ids], dtype=torch.long, device=self.model.watermark_device)
        values = processor.compute_g_values(tensor)
        mask = processor.compute_context_repetition_mask(tensor)
        for eos in self.model.eos_token_ids:
            mask &= processor.compute_eos_token_mask(tensor, eos)[
                :, self.config.ngram_len - 1 :
            ].bool()
        return values, mask

    def metadata(self) -> dict:
        return {
            "scheme": "synthid",
            "implementation": "transformers.SynthIDTextWatermarkingConfig",
            "detector": "SynthID raw mean-g"
            if self.config.statistic == "raw_mean"
            else "SynthID weighted mean",
            "calibrated": False,
            **self.config.model_dump(),
            "skip_first_ngram_calls": True,
        }

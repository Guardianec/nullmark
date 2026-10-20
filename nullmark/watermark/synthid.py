"""HF SynthID generation and reference mean scoring, without a trained detector."""

import torch
from transformers import SynthIDTextWatermarkingConfig

from nullmark.config import SynthIDConfig
from nullmark.models import CausalModel
from nullmark.watermark.base import DetectionResult, WatermarkScheme


class SynthIDScheme(WatermarkScheme):
    def __init__(self, model: CausalModel, config: SynthIDConfig, secret: dict):
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
        ids = self.model.encode(text)
        cfg = self.config
        if len(ids) < cfg.ngram_len:
            return DetectionResult(
                None, None, cfg.threshold, "mean_g", 0, status="insufficient_text"
            )
        processor = self.generation_config().construct_processor(
            self.model.model.config.vocab_size,
            self.model.settings.device,
        )
        tensor = torch.tensor([ids], dtype=torch.long, device=self.model.settings.device)
        values = processor.compute_g_values(tensor)
        mask = processor.compute_context_repetition_mask(tensor)
        eos = self.model.tokenizer.eos_token_id
        if eos is not None:
            mask &= processor.compute_eos_token_mask(tensor, eos)[:, cfg.ngram_len - 1 :].bool()
        count = int(mask.sum().item())
        if count == 0:
            return DetectionResult(
                None, None, cfg.threshold, "mean_g", 0, status="insufficient_text"
            )
        # Reference mean statistic: sum of unmasked g-values / (depth * unmasked contexts).
        score = float(values[mask].float().mean().item())
        return DetectionResult(score, score > cfg.threshold, cfg.threshold, "mean_g", count)

    def metadata(self) -> dict:
        return {
            "scheme": "synthid",
            "implementation": "transformers.SynthIDTextWatermarkingConfig",
            "detector": "reference_mean_g",
            "calibrated": False,
            **self.config.model_dump(),
            "skip_first_ngram_calls": True,
        }

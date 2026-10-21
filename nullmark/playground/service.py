"""Single-user playground state. Masters stay in memory; no key files are served."""

from dataclasses import asdict
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import Field

from nullmark.config import KGWConfig, ModelConfig, StrictConfig, SynthIDConfig
from nullmark.evaluation.calibration import (
    CalibratedDetector,
    conditions,
    uncalibrated,
)
from nullmark.evaluation.inspection import paired_generation
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.models import TextGenerationBackend, load_model
from nullmark.models.ollama import resolve_model
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme

GPT2_REVISION = "607a30d783dfa663caf39e06633721c8d4cfcd7e"


class AttackSettings(StrictConfig):
    generation_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    attack: Literal["random_edit", "synonym_replace", "paraphrase", "entropy_rewrite", "skd"]
    budget: float | None = Field(None, gt=0, le=0.2)
    edits: Literal[1, 2, 3, 5] = 3
    selection: Literal["skd", "random_pool", "entropy_only", "context_only", "tokenizer_only"] = (
        "skd"
    )
    seed: int = Field(42, ge=0, lt=2**32 - 1)


class PlaygroundSettings(StrictConfig):
    calibration_id: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")
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
    def __init__(self, *, keys=None, calibrations=()):
        self._keys = keys or KeyStore.create()
        self.calibrations: dict[str, CalibratedDetector] = {
            c.calibration_id: c for c in calibrations
        }
        self._models: dict[tuple, TextGenerationBackend] = {}
        self.lock = Lock()
        self.last_result = None
        self.last_settings = None
        self.last_model_config = None
        self.semantic = None

    def fresh_key(self) -> dict:
        self._keys = KeyStore.create()
        self.last_result = None
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
        if scheme:
            artifact = self.calibrations.get(settings.calibration_id)
            context = conditions(model, scheme, result["key_ref"])
            for side in ("plain", "marked"):
                sample = result.get(side)
                if sample is None:
                    continue
                from nullmark.watermark.base import DetectionResult

                raw = DetectionResult(**sample["detection"])
                sample["visible_token_count"] = len(sample["detector_tokens"])
                if artifact:
                    try:
                        sample["detection"] = artifact.evaluate(raw, context=context)
                    except ValueError:
                        sample["detection"] = {
                            **uncalibrated(raw),
                            "status": "incompatible_calibration",
                        }
                else:
                    sample["detection"] = uncalibrated(raw)
        result["generation_id"] = uuid4().hex
        self.last_result = result
        self.last_settings = settings
        self.last_model_config = config
        return result

    def attack(self, settings: AttackSettings) -> dict:
        from pathlib import Path

        from nullmark.attacks.base import AttackInput
        from nullmark.evaluation.attack_metrics import outcome
        from nullmark.evaluation.attack_worker import AttackWorker
        from nullmark.evaluation.quality import SemanticSimilarity, quality_metrics, text_diff

        original = self.last_result
        if original is None or original["generation_id"] != settings.generation_id:
            raise ValueError("Generate a sample before attacking it")
        if original["scheme"] == "none":
            raise ValueError("Select a watermark scheme before attacking")
        if settings.attack not in ("paraphrase", "skd") and settings.budget is None:
            raise ValueError("Sparse attacks require an edit budget")
        public_model = None
        if settings.attack != "random_edit":
            local = resolve_model("qwen3.5:9b-q4_K_M")
            public_model = {
                "model_path": str(local.path),
                "model_digest": local.blob_sha256,
                "offload": self.last_settings.offload,
            }
            if settings.attack == "skd":
                public_model.update(
                    skd_mode=True, semantic_cache=str(Path(".cache/huggingface/hub").resolve())
                )
        # Release GPU generation resources before the independent attack runtime.
        for model in self._models.values():
            model.close()
        self._models.clear()
        sample = AttackInput(
            original["generation_id"], self.last_settings.prompt, original["marked"]["text"]
        )
        with AttackWorker(model=public_model, cache=Path(".cache/playground-attacks")) as worker:
            attacked = worker.transform(
                sample,
                attack=settings.selection if settings.attack == "skd" else settings.attack,
                budget=settings.edits if settings.attack == "skd" else settings.budget,
                seed=settings.seed,
            )
        model = load_model(self.last_model_config)
        try:
            warnings = []
            if self.semantic is None:
                try:
                    self.semantic = SemanticSimilarity()
                except (ImportError, ValueError, OSError):
                    warnings.append(
                        "Semantic similarity unavailable; install/cache the pinned evaluator"
                    )
            quality = quality_metrics(
                sample.text, attacked.text, tokenize=model.encode, semantic=self.semantic
            )
            name = original["scheme"]
            private = self._keys.derive(
                name, self.last_settings.key_index, self.last_settings.synthid.depth
            )
            scheme = (
                KGWScheme(model, self.last_settings.kgw, private)
                if name == "kgw"
                else SynthIDScheme(model, self.last_settings.synthid, private)
            )
            artifact = self.calibrations.get(self.last_settings.calibration_id)
            raw = scheme.detect(attacked.text)
            context = conditions(model, scheme, original["key_ref"])
            before = original["marked"]["detection"]
            if artifact:
                try:
                    after = artifact.evaluate(raw, context=context)
                except ValueError:
                    if before["state"] == "DETECTED":
                        raise
                    after = {**uncalibrated(raw), "status": "incompatible_calibration"}
            else:
                after = uncalibrated(raw)
            eligible = before["state"] == "DETECTED"
            message = (
                "Eligible detected baseline."
                if eligible
                else "This sample is not eligible for evasion evaluation because the original "
                "watermark was not detected by the frozen evaluator."
                if before["state"] == "NOT DETECTED"
                else "The original sample has insufficient detector evidence."
            )
            return {
                "original": sample.text,
                "attack": asdict(attacked),
                "quality": quality,
                "diff": text_diff(sample.text, attacked.text),
                "before": before,
                "after": after,
                "eligible": eligible,
                "eligibility_message": message,
                "outcome": outcome(before, after),
                "warnings": warnings,
            }
        finally:
            model.close()

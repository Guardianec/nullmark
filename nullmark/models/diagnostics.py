"""Opt-in local model checks, never a CI download or a calibrated experiment."""

from dataclasses import asdict

import torch

from nullmark.config import KGWConfig, ModelConfig, SynthIDConfig
from nullmark.evaluation.secrets import KeyStore
from nullmark.models.gguf import GGUFBackend
from nullmark.models.ollama import LocalModelError, resolve_model
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme


def check_ollama(name: str, *, offload: str = "auto", tokens: int = 128) -> dict:
    local = resolve_model(name)
    config = ModelConfig(
        backend="ollama-gguf",
        name=name,
        revision=local.blob_sha256,
        offload=offload,
        threads=8,
        temperature=0.8,
        top_k=40,
        top_p=0.95,
        max_new_tokens=tokens,
    )
    model = GGUFBackend(config, local)
    try:
        raw = "Local tokenizer round trip."
        if model.decode(model.encode(raw)) != raw:
            raise LocalModelError("The local tokenizer failed its round-trip check.")
        prompt = "Explain photosynthesis in one clear paragraph for a high-school student."
        plain = model.generate(prompt, seed=101)
        replay = model.generate(prompt, seed=101)
        if plain.token_ids != replay.token_ids:
            raise LocalModelError("Same-seed generation did not replay on this backend/device.")
        target = model.encode(" banana")[-1]

        def force(input_ids, scores):
            result = torch.full_like(scores, float("-inf"))
            result[:, target] = 0
            return result

        model.settings = config.model_copy(update={"max_new_tokens": 16})
        biased = model.generate(prompt, seed=101, processor=force)
        if biased.token_ids != [target] * 16 or biased.processor_calls != 16:
            raise LocalModelError("Custom logits processing did not control every sampled token.")
        model.settings = config
        if model.generate(prompt, seed=101).token_ids != plain.token_ids:
            raise LocalModelError(
                "Removing the custom processor did not restore ordinary generation."
            )
        keys = KeyStore.create()
        kgw = KGWScheme(model, KGWConfig(), keys.derive("kgw", 0))
        wrong = KGWScheme(model, KGWConfig(), keys.derive("kgw", 1))
        synthid = SynthIDScheme(model, SynthIDConfig(), keys.derive("synthid", 0))
        rows = []
        for seed in (101, 202, 303):
            control = model.generate(prompt, seed=seed)
            marked_kgw = kgw.generate(model, prompt, seed=seed)
            marked_synthid = synthid.generate(model, prompt, seed=seed)
            rows.append(
                {
                    "seed": seed,
                    "plain_kgw": asdict(kgw.detect(control.text)),
                    "marked_kgw": asdict(kgw.detect(marked_kgw.text)),
                    "wrong_key_kgw": asdict(wrong.detect(marked_kgw.text)),
                    "plain_synthid": asdict(synthid.detect(control.text)),
                    "marked_synthid": asdict(synthid.detect(marked_synthid.text)),
                    "kgw_processor_calls": marked_kgw.processor_calls,
                    "synthid_processor_calls": marked_synthid.processor_calls,
                }
            )
        usable = all(
            all(
                row[field]["score"] is not None
                for field in (
                    "plain_kgw",
                    "marked_kgw",
                    "wrong_key_kgw",
                    "plain_synthid",
                    "marked_synthid",
                )
            )
            for row in rows
        )
        checks = {
            "tokenizer": True,
            "generation": True,
            "seed_replay": True,
            "custom_logits_every_token": True,
            "strong_bias": True,
            "processor_removal": True,
            "sufficient_text": usable,
        }
        checks["kgw_signal"] = usable and all(
            r["marked_kgw"]["score"] > max(r["plain_kgw"]["score"], r["wrong_key_kgw"]["score"])
            for r in rows
        )
        checks["synthid_signal"] = usable and all(
            r["marked_synthid"]["score"] > r["plain_synthid"]["score"] for r in rows
        )
        return {
            "model": model.metadata(),
            "checks": checks,
            "passed": all(checks.values()),
            "observations": rows,
            "plain_example": plain.text,
            "note": "Local smoke only. SynthID is uncalibrated; "
            "signal gain need not cross its threshold.",
        }
    finally:
        model.close()

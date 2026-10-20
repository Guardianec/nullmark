"""Experiment 003: fresh prompts, frozen baselines, blind workers, then evaluation."""

import hashlib
import json
from dataclasses import asdict
from time import perf_counter
from typing import Literal

import yaml
from pydantic import Field

from nullmark.attacks.base import AttackInput
from nullmark.attacks.baselines import NAMES
from nullmark.config import DatasetConfig, KGWConfig, ModelConfig, StrictConfig, SynthIDConfig
from nullmark.datasets import load_prompts
from nullmark.evaluation.attack_metrics import aggregate, outcome
from nullmark.evaluation.attack_worker import AttackWorker
from nullmark.evaluation.calibration import (
    CalibratedDetector,
    conditions,
    require_detected_baseline,
    require_frozen_evaluator,
)
from nullmark.evaluation.quality import SemanticSimilarity, quality_metrics
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.experiments.runner import environment, read_jsonl, sample_seed, write_json
from nullmark.models import load_model
from nullmark.models.ollama import resolve_model
from nullmark.watermark.registry import load_scheme

BUDGETS = (0.01, 0.02, 0.05, 0.10, 0.20)


class AttackBenchmarkConfig(StrictConfig):
    name: str = "003-baseline-attacks"
    seed: int = Field(20261021, ge=0, lt=2**32 - 1)
    model: ModelConfig
    dataset: DatasetConfig
    calibration_prompts: str
    calibrations: dict[str, str]
    kgw: KGWConfig = Field(default_factory=KGWConfig)
    synthid: SynthIDConfig = Field(
        default_factory=lambda: SynthIDConfig(depth=20, statistic="weighted_mean")
    )
    semantic: bool = True
    attack_offload: Literal["auto", "cpu", "gpu"] = "auto"


def validate_disjoint(prompts, calibration):
    def normalized(text):
        return " ".join(text.casefold().split())

    ids, texts = [p.id for p in prompts], [normalized(p.text) for p in prompts]
    if len(set(ids)) != len(ids) or len(set(texts)) != len(texts):
        raise ValueError("attack corpus contains duplicate ID or text")
    if set(ids) & {r["id"] for r in calibration} or set(texts) & {
        normalized(r["text"]) for r in calibration
    }:
        raise ValueError("attack and calibration datasets overlap")


def append(path, row):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, allow_nan=False) + "\n")


def run_benchmark(config_path, *, output, secrets_path, stage="all", resume=False):
    config = AttackBenchmarkConfig.model_validate(yaml.safe_load(config_path.read_text("utf-8")))
    base = config_path.parent
    prompts, digest = load_prompts(config.dataset, base)
    validate_disjoint(prompts, read_jsonl(base / config.calibration_prompts))
    if set(config.calibrations) != {"kgw", "synthid"}:
        raise ValueError("both frozen evaluators are required")
    keys = KeyStore.load(secrets_path)
    artifacts = {s: CalibratedDetector.load(base / p) for s, p in config.calibrations.items()}
    frozen_hashes = {
        s: hashlib.sha256((base / p).read_bytes()).hexdigest()
        for s, p in config.calibrations.items()
    }
    identity = {
        "config": config.model_dump(),
        "dataset_sha256": digest,
        "calibration_sha256": frozen_hashes,
        "key_refs": {s: key_reference(keys, s, 0) for s in artifacts},
    }
    if output.exists():
        if not resume or json.loads((output / "identity.json").read_text("utf-8")) != identity:
            raise ValueError("existing run requires resume with identical inputs")
    else:
        output.mkdir(parents=True)
        (output / "private").mkdir(mode=0o700)
        keys.save(output / "private" / "secrets.json")
        write_json(output / "identity.json", identity)
        write_json(
            output / "manifest.json",
            {**identity, "environment": environment(), "stage": "initialized"},
        )
        (output / "config.resolved.yaml").write_text(yaml.safe_dump(config.model_dump()), "utf-8")
        for name in ("source_samples", "baselines", "attack_inputs", "evaluation", "quality"):
            (output / f"{name}.jsonl").touch()
        (output / "attacks").mkdir()
        for attack in NAMES:
            (output / "attacks" / f"{attack}.jsonl").touch()

    def scheme_for(model, name):
        scheme = load_scheme(name, model, config, keys.derive(name, 0, config.synthid.depth))
        context = conditions(model, scheme, key_reference(keys, name, 0))
        require_frozen_evaluator(artifacts[name], context=context)
        return scheme, context

    if stage in ("all", "generate"):
        model = load_model(config.model)
        try:
            existing = {r["sample_id"] for r in read_jsonl(output / "baselines.jsonl")}
            for name in artifacts:
                scheme, context = scheme_for(model, name)
                for prompt in prompts:
                    sample_id = f"{name}:{prompt.id}"
                    if sample_id in existing:
                        continue
                    seed = sample_seed(config.seed, prompt.id, 0) % (2**32 - 1)
                    generated = scheme.generate(model, prompt.text, seed=seed)
                    raw = scheme.detect(generated.text)
                    before = artifacts[name].evaluate(raw, context=context)
                    if before["state"] == "DETECTED":
                        require_detected_baseline(artifacts[name], raw, context=context)
                    sample = AttackInput(sample_id, prompt.text, generated.text)
                    append(output / "source_samples.jsonl", asdict(sample))
                    if before["state"] == "DETECTED":
                        append(output / "attack_inputs.jsonl", asdict(sample))
                    append(
                        output / "baselines.jsonl",
                        {
                            "sample_id": sample_id,
                            "style": prompt.style,
                            "scheme": name,
                            "seed": seed,
                            "before": before,
                        },
                    )
                    print(f"baseline {sample_id}: {before['state']}", flush=True)
        finally:
            model.close()

    baselines = read_jsonl(output / "baselines.jsonl")
    sources = {
        r["sample_id"]: AttackInput(**r) for r in read_jsonl(output / "source_samples.jsonl")
    }
    eligible = [r for r in baselines if r["before"]["state"] == "DETECTED"]
    if stage in ("all", "attack", "evaluate") and len(baselines) != len(prompts) * 2:
        raise ValueError("complete baseline generation before attack/evaluation")
    if stage in ("all", "attack"):
        local = resolve_model(config.model.name, expected_digest=config.model.revision)
        public_model = {
            "model_path": str(local.path),
            "model_digest": local.blob_sha256,
            "offload": config.attack_offload,
        }
        with AttackWorker(model=public_model, cache=output / "attack-cache") as worker:
            for attack in NAMES:
                path = output / "attacks" / f"{attack}.jsonl"
                existing = {(r["sample_id"], r["budget"]) for r in read_jsonl(path)}
                for baseline in eligible:
                    sample = sources[baseline["sample_id"]]
                    for budget in (None,) if attack == "paraphrase" else BUDGETS:
                        if (sample.sample_id, budget) in existing:
                            continue
                        started = perf_counter()
                        row = {"sample_id": sample.sample_id, "attack": attack, "budget": budget}
                        try:
                            result = worker.transform(
                                sample, attack=attack, budget=budget, seed=baseline["seed"]
                            )
                            row["output"] = asdict(result)
                            row["failure"] = None
                        except (ValueError, RuntimeError, OSError) as exc:
                            row["failure"] = type(exc).__name__
                        row["runtime_seconds"] = perf_counter() - started
                        append(path, row)
                    print(f"attack {attack} {sample.sample_id}", flush=True)

    if stage in ("all", "evaluate"):
        expected_ids = {r["sample_id"] for r in eligible}
        for attack in NAMES:
            rows = read_jsonl(output / "attacks" / f"{attack}.jsonl")
            expected = {
                (sample_id, budget)
                for sample_id in expected_ids
                for budget in ((None,) if attack == "paraphrase" else BUDGETS)
            }
            actual = {(r["sample_id"], r["budget"]) for r in rows}
            if actual != expected or len(rows) != len(expected):
                raise ValueError(
                    "incomplete or duplicate attack attempts; resume attack stage first"
                )
        semantic = SemanticSimilarity() if config.semantic else None
        model = load_model(config.model)
        try:
            evaluators = {s: scheme_for(model, s) for s in artifacts}
            baseline_by_id = {r["sample_id"]: r for r in baselines}
            existing = {
                (r["sample_id"], r["attack"], r["budget"])
                for r in read_jsonl(output / "evaluation.jsonl")
            }
            for attack in NAMES:
                for row in read_jsonl(output / "attacks" / f"{attack}.jsonl"):
                    identity_row = (row["sample_id"], attack, row["budget"])
                    if identity_row in existing:
                        continue
                    baseline = baseline_by_id[row["sample_id"]]
                    evaluated = {**{k: v for k, v in row.items() if k != "output"}, **baseline}
                    evaluated["after"] = None
                    if not row["failure"]:
                        text = row["output"]["text"]
                        # Quality precedes the post-attack watermark detector.
                        quality = quality_metrics(
                            sources[row["sample_id"]].text,
                            text,
                            tokenize=model.encode,
                            semantic=semantic,
                        )
                        evaluated["quality"] = quality
                        append(
                            output / "quality.jsonl",
                            {
                                "sample_id": row["sample_id"],
                                "attack": attack,
                                "budget": row["budget"],
                                **quality,
                            },
                        )
                        scheme, context = evaluators[baseline["scheme"]]
                        evaluated["after"] = artifacts[baseline["scheme"]].evaluate(
                            scheme.detect(text), context=context
                        )
                    evaluated["outcome"] = outcome(
                        baseline["before"], evaluated["after"], failure=bool(row["failure"])
                    )
                    append(output / "evaluation.jsonl", evaluated)
        finally:
            model.close()
        from nullmark.experiments.attack_report import report

        metrics = aggregate(baselines, read_jsonl(output / "evaluation.jsonl"))
        write_json(output / "metrics.json", metrics)
        report(output, metrics)
        manifest = json.loads((output / "manifest.json").read_text("utf-8"))
        manifest["stage"] = "complete"
        manifest["expected_attempts"] = len(eligible) * 16
        manifest["evaluated_attempts"] = len(read_jsonl(output / "evaluation.jsonl"))
        write_json(output / "manifest.json", manifest)
    # Frozen evaluator files must remain byte-for-byte unchanged.
    assert frozen_hashes == {
        s: hashlib.sha256((base / p).read_bytes()).hexdigest()
        for s, p in config.calibrations.items()
    }
    return output

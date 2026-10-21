"""Experiment 004: pre-registered blind pools and fixed matched-edit comparisons."""

import hashlib
import json
import subprocess
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field

from nullmark.attacks.base import AttackInput
from nullmark.attacks.skd import BUDGETS, DEFAULTS, METHODS, settings
from nullmark.datasets import load_prompts
from nullmark.evaluation.attack_metrics import aggregate, outcome
from nullmark.evaluation.attack_worker import AttackWorker
from nullmark.evaluation.calibration import CalibratedDetector, conditions, require_frozen_evaluator
from nullmark.evaluation.quality import SemanticSimilarity, quality_metrics
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.experiments.attacks import (
    AttackBenchmarkConfig,
    append,
    run_benchmark,
    validate_disjoint,
)
from nullmark.experiments.runner import environment, read_jsonl, write_json
from nullmark.models import load_model
from nullmark.models.ollama import resolve_model
from nullmark.watermark.registry import load_scheme

DESIGN_FILES = (
    "nullmark/attacks/base.py",
    "nullmark/attacks/baselines.py",
    "nullmark/attacks/text.py",
    "nullmark/attacks/skd.py",
    "nullmark/attacks/model.py",
    "nullmark/attacks/worker.py",
    "nullmark/common/semantic.py",
    "nullmark/common/runtime.py",
    "nullmark/evaluation/attack_worker.py",
    "nullmark/experiments/skd.py",
    "nullmark/experiments/skd_report.py",
    "configs/benchmarks/qwen-skd.yaml",
    "configs/benchmarks/skd-v1.jsonl",
    "docs/skd.md",
)


class SKDBenchmarkConfig(AttackBenchmarkConfig):
    name: str = "004-skd"
    seed: int = Field(20261023, ge=0, lt=2**32 - 1)
    baseline_prompts: str = "attacks-v1.jsonl"
    development_prompts: str = "skd-dev-v1.jsonl"
    skd: dict = Field(default_factory=lambda: settings())


def verify_design(commit):
    root = Path(__file__).resolve().parents[2]
    if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        raise ValueError("full pre-registration commit SHA required")
    for name in DESIGN_FILES:
        frozen = subprocess.run(
            ["git", "show", f"{commit}:{name}"], cwd=root, capture_output=True, check=True
        ).stdout
        if frozen != (root / name).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("attack protocol differs from pre-registration: " + name)


def public_id(sample_id):
    return hashlib.sha256(sample_id.encode()).hexdigest()[:24]


def run_skd(config_path, *, output, secrets_path, design_commit, stage="all", resume=False):
    config = SKDBenchmarkConfig.model_validate(yaml.safe_load(config_path.read_text("utf-8")))
    protocol = settings(config.skd)
    if protocol != DEFAULTS:
        raise ValueError("v0.3 benchmark uses the pre-registered default protocol only")
    verify_design(design_commit)
    base = config_path.resolve().parent
    prompts, digest = load_prompts(config.dataset, base)
    for old in (config.calibration_prompts, config.baseline_prompts, config.development_prompts):
        validate_disjoint(prompts, read_jsonl(base / old))
    identity = {
        "config": config.model_dump(),
        "dataset_sha256": digest,
        "design_commit": design_commit,
        "frozen_evaluators": {
            s: hashlib.sha256((base / p).read_bytes()).hexdigest()
            for s, p in config.calibrations.items()
        },
        "key_refs": {
            s: key_reference(KeyStore.load(secrets_path), s, 0) for s in config.calibrations
        },
    }
    if output.exists():
        if not resume or json.loads((output / "identity.json").read_text("utf-8")) != identity:
            raise ValueError("existing SKD run requires identical inputs and resume")
    else:
        output.mkdir(parents=True)
        write_json(output / "identity.json", identity)
        write_json(
            output / "manifest.json",
            {**identity, "environment": environment(), "stage": "initialized"},
        )
        (output / "attacks").mkdir()
        (output / "candidates").mkdir()
        for name in METHODS:
            (output / "attacks" / f"{name}.jsonl").touch()
        for name in ("evaluation", "quality", "attack_inputs"):
            (output / f"{name}.jsonl").touch()
        (output / "candidates/candidates.jsonl").touch()
    resolved = config.model_dump()
    for name in ("calibration_prompts", "baseline_prompts", "development_prompts"):
        resolved[name] = str(base / resolved[name])
    resolved["dataset"]["path"] = str(base / config.dataset.path)
    resolved["calibrations"] = {s: str(base / p) for s, p in config.calibrations.items()}
    (output / "config.resolved.yaml").write_text(yaml.safe_dump(resolved), "utf-8")
    generator = output / "generation"
    if stage in ("all", "generate"):
        # Reuse the frozen v0.2 generation/eligibility path, with the fresh corpus only.
        old = {k: v for k, v in resolved.items() if k in AttackBenchmarkConfig.model_fields}
        source_config = output / "generation.yaml"
        source_config.write_text(yaml.safe_dump(old), "utf-8")
        run_benchmark(
            source_config,
            output=generator,
            secrets_path=secrets_path,
            stage="generate",
            resume=generator.exists(),
        )
    baselines = read_jsonl(generator / "baselines.jsonl")
    if stage != "generate" and len(baselines) != len(prompts) * 2:
        raise ValueError("finish baseline generation first")
    sources = {
        r["sample_id"]: AttackInput(public_id(r["sample_id"]), r["prompt"], r["text"])
        for r in read_jsonl(generator / "source_samples.jsonl")
    }
    eligible = [r for r in baselines if r["before"]["state"] == "DETECTED"]
    (output / "source_samples.jsonl").write_bytes((generator / "source_samples.jsonl").read_bytes())
    (output / "attack_inputs.jsonl").write_text(
        "".join(json.dumps(asdict(sources[b["sample_id"]])) + "\n" for b in eligible), "utf-8"
    )
    if stage in ("all", "attack"):
        local = resolve_model(config.model.name, expected_digest=config.model.revision)
        resource = {
            "model_path": str(local.path),
            "model_digest": local.blob_sha256,
            "offload": config.attack_offload,
            "skd_mode": True,
            "semantic_cache": str(Path(".cache/huggingface/hub").resolve()),
        }
        done = {
            m: {
                (r["sample_id"], r["budget"]) for r in read_jsonl(output / "attacks" / f"{m}.jsonl")
            }
            for m in METHODS
        }
        pools = {r["sample_id"] for r in read_jsonl(output / "candidates/candidates.jsonl")}
        with AttackWorker(model=resource, cache=output / "attack-cache", timeout=1800) as worker:
            for baseline in eligible:
                sid = baseline["sample_id"]
                for method in METHODS:
                    for k in BUDGETS:
                        if (sid, k) in done[method]:
                            continue
                        row = {"sample_id": sid, "attack": method, "budget": k}
                        try:
                            result = worker.transform(
                                sources[sid],
                                attack=method,
                                budget=k,
                                seed=baseline["seed"],
                                skd=protocol,
                            )
                            artifact = result.skd
                            if sources[sid].sample_id not in pools:
                                append(
                                    output / "candidates/candidates.jsonl",
                                    {
                                        key: artifact[key]
                                        for key in (
                                            "sample_id",
                                            "pool_sha256",
                                            "candidates",
                                            "coverage",
                                            "rejections",
                                            "generation_seconds",
                                            "config",
                                            "version",
                                        )
                                    },
                                )
                                pools.add(sources[sid].sample_id)
                            # Keep full candidate details in the shared artifact only.
                            content = asdict(result)
                            content["skd"] = {
                                key: value for key, value in artifact.items() if key != "candidates"
                            }
                            row.update(
                                output=content,
                                failure=None,
                                runtime_seconds=result.runtime_seconds
                                + artifact["generation_seconds"],
                            )
                        except (ValueError, RuntimeError, OSError) as exc:
                            row.update(failure=type(exc).__name__, runtime_seconds=0.0)
                        append(output / "attacks" / f"{method}.jsonl", row)
                print("SKD finalized " + sid, flush=True)
    if stage in ("all", "evaluate"):
        attempts = []
        for method in METHODS:
            rows = read_jsonl(output / "attacks" / f"{method}.jsonl")
            expected = {(b["sample_id"], k) for b in eligible for k in BUDGETS}
            if {(r["sample_id"], r["budget"]) for r in rows} != expected or len(rows) != len(
                expected
            ):
                raise ValueError("complete all fixed attack attempts before evaluation")
            attempts.extend(rows)
        # No detector is constructed until ALL selectors' outputs are immutable on disk.
        semantic = (
            SemanticSimilarity(cache_folder=str(Path(".cache/huggingface/hub").resolve()))
            if config.semantic
            else None
        )
        keys = KeyStore.load(secrets_path)
        model = load_model(config.model)
        try:
            evaluators = {}
            for name, path in config.calibrations.items():
                scheme = load_scheme(
                    name, model, config, keys.derive(name, 0, config.synthid.depth)
                )
                context = conditions(model, scheme, key_reference(keys, name, 0))
                artifact = CalibratedDetector.load(base / path)
                require_frozen_evaluator(artifact, context=context)
                evaluators[name] = (scheme, context, artifact)

            @lru_cache(maxsize=8192)
            def quality(before, after):
                return quality_metrics(before, after, tokenize=model.encode, semantic=semantic)

            @lru_cache(maxsize=8192)
            def detect(name, text):
                scheme, context, artifact = evaluators[name]
                return artifact.evaluate(scheme.detect(text), context=context)

            by_id = {r["sample_id"]: r for r in baselines}
            done = {
                (r["sample_id"], r["attack"], r["budget"])
                for r in read_jsonl(output / "evaluation.jsonl")
            }
            for row in attempts:
                if (row["sample_id"], row["attack"], row["budget"]) in done:
                    continue
                baseline = by_id[row["sample_id"]]
                evaluated = {
                    **{k: v for k, v in row.items() if k != "output"},
                    **baseline,
                    "after": None,
                }
                if not row["failure"]:
                    evaluated["skd"] = row["output"]["skd"]
                    evaluated["quality"] = quality(
                        sources[row["sample_id"]].text, row["output"]["text"]
                    )
                    evaluated["after"] = detect(baseline["scheme"], row["output"]["text"])
                evaluated["outcome"] = outcome(
                    baseline["before"], evaluated["after"], failure=bool(row["failure"])
                )
                append(output / "evaluation.jsonl", evaluated)
        finally:
            model.close()
        from nullmark.experiments.skd_report import report

        evaluated = read_jsonl(output / "evaluation.jsonl")
        (output / "quality.jsonl").write_text(
            "".join(
                json.dumps(
                    {
                        "sample_id": r["sample_id"],
                        "attack": r["attack"],
                        "budget": r["budget"],
                        **r["quality"],
                    }
                )
                + "\n"
                for r in evaluated
                if "quality" in r
            ),
            "utf-8",
        )
        metrics = aggregate(baselines, evaluated)
        write_json(output / "metrics.json", metrics)
        report(output, metrics, baselines, evaluated)
        manifest = json.loads((output / "manifest.json").read_text("utf-8"))
        manifest.update(
            stage="complete",
            expected_attempts=len(eligible) * 20,
            evaluated_attempts=len(evaluated),
        )
        write_json(output / "manifest.json", manifest)
    if identity["frozen_evaluators"] != {
        s: hashlib.sha256((base / p).read_bytes()).hexdigest()
        for s, p in config.calibrations.items()
    }:
        raise ValueError("frozen evaluator changed")
    return output

"""Trusted generation and evaluation orchestration; no detector calls inside attacks."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import torch
import yaml

from nullmark import __version__
from nullmark.attacks.base import AttackInput
from nullmark.config import ExperimentConfig, load_config
from nullmark.datasets import load_prompts
from nullmark.evaluation.metrics import summarize, summary_markdown
from nullmark.evaluation.records import export_sample
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.models import load_model
from nullmark.watermark.registry import SCHEMES, load_scheme


def sample_seed(seed: int, prompt_id: str, key_index: int) -> int:
    label = json.dumps(["nullmark-v1", seed, prompt_id, key_index])
    return int.from_bytes(hashlib.sha256(label.encode()).digest()[:4], "big")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def environment() -> dict:
    def git(*args):
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None

    try:
        revision = git("rev-parse", "HEAD")
        dirty = bool(git("status", "--porcelain")) if revision else None
    except OSError:
        revision, dirty = None, None
    return {
        "nullmark": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "git_revision": revision,
        "git_dirty": dirty,
        "packages": dict(
            sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
        ),
    }


def run_experiment(
    config_path: Path,
    *,
    output: Path | None = None,
    secrets_path: Path | None = None,
) -> Path:
    config = load_config(config_path)
    return run(config, base=config_path.parent, output=output, secrets_path=secrets_path)


def run(
    config: ExperimentConfig,
    *,
    base: Path,
    output: Path | None = None,
    secrets_path: Path | None = None,
) -> Path:
    started = perf_counter()
    prompts, dataset_hash = load_prompts(config.dataset, base)
    keys = KeyStore.load(secrets_path) if secrets_path else KeyStore.create()
    output = output or Path("results") / config.name / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    )
    output.mkdir(parents=True, exist_ok=False)
    private = output / "private"
    private.mkdir(mode=0o700)
    keys.save(private / "secrets.json")
    resolved = config.model_dump()
    resolved["dataset"] = {"source": "jsonl", "path": "prompts.jsonl", "sample_count": len(prompts)}
    (output / "config.resolved.yaml").write_text(yaml.safe_dump(resolved), encoding="utf-8")
    (output / "prompts.jsonl").write_text(
        "".join(json.dumps(asdict(p)) + "\n" for p in prompts),
        encoding="utf-8",
    )
    model = load_model(config.model)
    manifest = {
        "version": 1,
        "experiment_id": config.name,
        "run_id": output.name,
        "purpose": config.purpose,
        "dataset_source": config.dataset.source,
        "dataset_sha256": dataset_hash,
        "model": model.metadata(),
        "sampling": {
            "seed": config.seed,
            "temperature": config.model.temperature,
            "top_k": config.model.top_k,
            "top_p": config.model.top_p,
        },
        "environment": environment(),
        "expected_generations": len(prompts) * config.random_keys * 3,
        "expected_detections": len(prompts) * config.random_keys * 4,
        "detection_input": "retokenized continuation text; prompt excluded",
        "secret_derivation": "HMAC-SHA256 nullmark-v1; master in private/secrets.json",
    }
    write_json(output / "manifest.json", manifest)
    records, evaluations, failures = [], [], []
    with (
        (output / "public_samples.jsonl").open("w", encoding="utf-8") as samples_file,
        (output / "generation.jsonl").open("w", encoding="utf-8") as generation_file,
        (output / "evaluation.jsonl").open("w", encoding="utf-8") as evaluation_file,
        (private / "tokens.jsonl").open("w", encoding="utf-8") as tokens_file,
        (output / "failures.jsonl").open("w", encoding="utf-8") as failures_file,
    ):

        def append(handle, row):
            handle.write(json.dumps(row, allow_nan=False) + "\n")
            handle.flush()

        def failure(stage, sample_id, exc, detector=None):
            # Exception messages can contain upstream private configuration; export type only.
            row = {
                "stage": stage,
                "sample_id": sample_id,
                "error_type": type(exc).__name__,
                "detector": detector,
            }
            failures.append(row)
            append(failures_file, row)

        for index in range(config.random_keys):
            schemes = {
                name: load_scheme(
                    name, model, config, keys.derive(name, index, config.synthid.depth)
                )
                for name in SCHEMES
            }
            refs = {name: key_reference(keys, name, index) for name in SCHEMES}
            for prompt in prompts:
                seed = sample_seed(config.seed, prompt.id, index)
                for name in ("none", *SCHEMES):
                    sample_id = f"{prompt.id}-k{index}-{name}"
                    try:
                        generated = (
                            model.generate(prompt.text, seed=seed)
                            if name == "none"
                            else schemes[name].generate(model, prompt.text, seed=seed)
                        )
                    except (RuntimeError, ValueError) as exc:
                        failure("generation", sample_id, exc)
                        continue
                    sample = AttackInput(sample_id, prompt.text, generated.text)
                    record = {
                        "sample_id": sample_id,
                        "prompt_id": prompt.id,
                        "prompt_style": prompt.style,
                        "seed": seed,
                        "sampling": {
                            "temperature": config.model.temperature,
                            "top_k": config.model.top_k,
                            "top_p": config.model.top_p,
                        },
                        "watermark_scheme": name,
                        "key_index": index,
                        "key_ref": refs.get(name),
                        "watermark_public_config": (
                            schemes[name].metadata() if name != "none" else None
                        ),
                        "token_count": len(generated.token_ids),
                        "text_token_count": len(model.encode(generated.text)),
                        "text_roundtrip_exact": model.encode(generated.text) == generated.token_ids,
                        "generation_seconds": generated.seconds,
                    }
                    records.append(record)
                    append(samples_file, export_sample(sample))
                    append(generation_file, record)
                    append(
                        tokens_file,
                        {
                            "sample_id": sample_id,
                            "token_ids": generated.token_ids,
                            "prompt_token_ids": generated.prompt_token_ids,
                        },
                    )
                    for detector_name in SCHEMES if name == "none" else (name,):
                        try:
                            detected = schemes[detector_name].detect(generated.text)
                        except (RuntimeError, ValueError) as exc:
                            failure("detection", sample_id, exc, detector_name)
                            continue
                        row = {
                            "sample_id": sample_id,
                            "detector": detector_name,
                            "watermarked": name != "none",
                            "key_index": index,
                            "key_ref": refs[detector_name],
                            "detection": detected.to_dict(),
                        }
                        evaluations.append(row)
                        append(evaluation_file, row)
    metrics = summarize(records, evaluations, failures, perf_counter() - started)
    metrics["purpose"] = config.purpose
    write_json(output / "metrics.json", metrics)
    (output / "summary.md").write_text(summary_markdown(metrics, config.purpose), encoding="utf-8")
    model.close()
    return output

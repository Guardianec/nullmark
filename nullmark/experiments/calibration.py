"""Experiment 002: independent prompt splits, clean-only fitting, frozen evaluation."""

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from uuid import uuid4

import yaml
from pydantic import Field, model_validator

from nullmark.config import DatasetConfig, KGWConfig, ModelConfig, StrictConfig, SynthIDConfig
from nullmark.datasets import Prompt, load_prompts
from nullmark.evaluation.calibration import (
    CalibratedDetector,
    canonical,
    conditions,
    token_diagnostic,
)
from nullmark.evaluation.secrets import KeyStore, key_reference
from nullmark.experiments.runner import environment, sample_seed, write_json
from nullmark.models import load_model
from nullmark.watermark.base import DetectionResult
from nullmark.watermark.kgw import KGWScheme
from nullmark.watermark.synthid import SynthIDScheme

BUCKETS = (
    ("<64", 0, 64),
    ("64–127", 64, 128),
    ("128–255", 128, 256),
    ("256–511", 256, 512),
    ("512+", 512, math.inf),
)


class CalibrationConfig(StrictConfig):
    name: str = Field("002_detector_calibration", pattern=r"^[a-zA-Z0-9_-]+$")
    seed: int = Field(20261020, ge=0, lt=2**32)
    calibration_count: int = Field(100, ge=1)
    evaluation_count: int = Field(100, ge=1)
    target_fprs: list[float] = Field(default_factory=lambda: [0.01])
    depths: list[int] = Field(default_factory=lambda: [10, 20, 30])
    minimum_usable_tokens: int = Field(64, ge=1)
    model: ModelConfig = Field(default_factory=ModelConfig)
    dataset: DatasetConfig = Field(default_factory=lambda: DatasetConfig(sample_count=200))
    synthid: SynthIDConfig = Field(default_factory=SynthIDConfig)
    kgw: KGWConfig = Field(default_factory=KGWConfig)

    @model_validator(mode="after")
    def valid_study(self):
        if (
            not self.target_fprs
            or len(set(self.target_fprs)) != len(self.target_fprs)
            or any(not 0 < a < 1 for a in self.target_fprs)
        ):
            raise ValueError("target FPRs must be distinct values between zero and one")
        if (
            not self.depths
            or len(set(self.depths)) != len(self.depths)
            or any(d < 1 or d > 30 for d in self.depths)
        ):
            raise ValueError("depths must be distinct integers between 1 and 30")
        return self


def split_prompts(
    prompts: list[Prompt], calibration_count: int, evaluation_count: int, seed: int
) -> dict[str, list[Prompt]]:
    if calibration_count + evaluation_count > len(prompts):
        raise ValueError("not enough independent prompts for the requested split")
    if len({p.id for p in prompts}) != len(prompts) or len({p.text for p in prompts}) != len(
        prompts
    ):
        raise ValueError("duplicate prompt IDs or texts would leak between splits")
    # Shuffle within each style, then interleave styles to balance diversity.
    rng = random.Random(seed)
    groups = defaultdict(list)
    for prompt in sorted(prompts, key=lambda p: p.id):
        groups[prompt.style].append(prompt)
    for style in sorted(groups):
        rng.shuffle(groups[style])
    ordered = []
    while any(groups.values()):
        for style in sorted(groups):
            if groups[style]:
                ordered.append(groups[style].pop())
    # Alternate assignment so both partitions cover every style for small runs.
    splits = {"calibration": [], "evaluation": []}
    style_counts = {s: defaultdict(int) for s in splits}
    counts = {"calibration": calibration_count, "evaluation": evaluation_count}
    for prompt in ordered:
        available = [s for s in splits if len(splits[s]) < counts[s]]
        if not available:
            break
        side = min(
            available,
            key=lambda s: (style_counts[s][prompt.style] / counts[s], len(splits[s]) / counts[s]),
        )
        splits[side].append(prompt)
        style_counts[side][prompt.style] += 1
    return splits


def distribution(values: list[float]) -> dict:
    if not values:
        return {"count": 0}
    values = sorted(values)
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "min": values[0],
        "max": values[-1],
        "p05": values[math.ceil(0.05 * len(values)) - 1],
        "p95": values[math.ceil(0.95 * len(values)) - 1],
    }


def rate(successes: int, total: int) -> dict:
    if not total:
        return {"value": None, "numerator": successes, "denominator": 0, "wilson95": None}
    p, z = successes / total, 1.959963984540054
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total**2)) / (1 + z * z / total)
    return {
        "value": p,
        "numerator": successes,
        "denominator": total,
        "wilson95": [max(0, center - half), min(1, center + half)],
    }


def evaluate_rows(rows: list[dict], artifact: CalibratedDetector, context: dict) -> dict:
    decisions = [
        (r, artifact.evaluate(DetectionResult(**r["detection"]), context=context)) for r in rows
    ]
    clean = [d for r, d in decisions if not r["watermarked"]]
    marked = [d for r, d in decisions if r["watermarked"]]
    usable_clean = [d for d in clean if d["prediction"] is not None]
    usable_marked = [d for d in marked if d["prediction"] is not None]
    tp = sum(d["prediction"] is True for d in usable_marked)
    fp = sum(d["prediction"] is True for d in usable_clean)
    return {
        "class_balance": {"clean": len(clean), "marked": len(marked)},
        "usable_sample_count": len(usable_clean) + len(usable_marked),
        "tpr": rate(tp, len(usable_marked)),
        "fpr": rate(fp, len(usable_clean)),
        "specificity": rate(len(usable_clean) - fp, len(usable_clean)),
        "abstention_rate": rate(len(rows) - len(usable_clean) - len(usable_marked), len(rows)),
        "marked_detection_yield": rate(tp, len(marked)),
        "clean_abstention_rate": rate(len(clean) - len(usable_clean), len(clean)),
        "marked_abstention_rate": rate(len(marked) - len(usable_marked), len(marked)),
        "distributions": {
            name: distribution([d["score"] for d in values if d["score"] is not None])
            for name, values in (("clean", clean), ("marked", marked))
        },
        "precision": None,
        "precision_note": "Deployment prevalence not specified.",
    }


def diagnostics(rows: list[dict]) -> dict:
    deltas = [r["score_delta"] for r in rows if r["score_delta"] is not None]
    absolute = distribution([abs(d) for d in deltas])
    return {
        "mean_delta": mean(deltas) if deltas else None,
        "median_delta": median(deltas) if deltas else None,
        "p95_absolute_delta": absolute.get("p95"),
        "exact_roundtrip_fraction": mean(r["token_roundtrip_exact"] for r in rows),
        "note": "Native minus visible; EOG controls alone can prevent exact round trips.",
        "score_delta_distribution": distribution(deltas),
    }


def distribution_plot(rows: list[dict], artifact: CalibratedDetector, path: Path) -> None:
    """Small dependency-free held-out histogram; raw data remains authoritative."""
    values = [r["visible_score"] for r in rows if r["visible_score"] is not None]
    if not values:
        return
    threshold = artifact.operating_point.empirical_threshold
    lo, hi = min(*values, threshold), max(*values, threshold)
    width = hi - lo or 1
    bins = [[0] * 20 for _ in range(2)]
    for row in rows:
        score = row["visible_score"]
        if score is not None:
            bins[int(row["watermarked"])][min(19, int(20 * (score - lo) / width))] += 1
    peak = max(1, *bins[0], *bins[1])
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 280" role="img">',
        f"<title>{escape(artifact.scheme)} {escape(artifact.statistic)} held-out scores</title>",
        '<rect width="640" height="280" fill="white"/>',
        '<text x="40" y="22">Held-out scores: gray clean; green marked; dashed threshold</text>',
    ]
    for marked, color in ((0, "#87968c"), (1, "#146957")):
        for index, count in enumerate(bins[marked]):
            height = 180 * count / peak
            svg.append(
                f'<rect x="{40 + index * 28 + marked * 13}" y="{220 - height}" '
                f'width="13" height="{height}" fill="{color}"/>'
            )
    x = 40 + 560 * (threshold - lo) / width
    svg.extend(
        [
            f'<path d="M {x} 35 V 225" stroke="#a16c3b" stroke-dasharray="4 4"/>',
            f'<text x="40" y="250">{lo:.5f}</text>',
            f'<text x="520" y="250">{hi:.5f}</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(svg), "utf-8")


def summarize_run(output: Path) -> dict:
    rows = [json.loads(line) for line in (output / "scores.jsonl").read_text("utf-8").splitlines()]
    manifest = json.loads((output / "manifest.json").read_text("utf-8"))
    reports = {}
    for name, context in manifest["conditions"].items():
        selected = [r for r in rows if r["detector_id"] == name]
        calibration = [r for r in selected if r["split"] == "calibration"]
        evaluation = [r for r in selected if r["split"] == "evaluation"]
        for alpha in manifest["target_fprs"]:
            path = output / f"{name}-fpr-{alpha:g}.calibration.json"
            if path.exists():
                artifact = CalibratedDetector.load(path)
            else:
                artifact = CalibratedDetector.fit(
                    scheme="kgw" if name == "kgw-z_score" else "synthid",
                    statistic=calibration[0]["detection"]["statistic"],
                    clean=[
                        DetectionResult(**r["detection"])
                        for r in calibration
                        if not r["watermarked"]
                    ],
                    target_fpr=alpha,
                    context=context,
                    dataset_hash=manifest["calibration_dataset_hash"],
                    minimum_usable_tokens=manifest["minimum_usable_tokens"],
                )
                artifact.save(path)
            metrics = evaluate_rows(evaluation, artifact, context)
            metrics["by_usable_length"] = {
                label: evaluate_rows(
                    [r for r in evaluation if lo <= r["usable_detector_token_count"] < hi],
                    artifact,
                    context,
                )
                for label, lo, hi in BUCKETS
            }
            metrics["by_visible_length"] = {
                label: evaluate_rows(
                    [r for r in evaluation if lo <= r["retokenized_token_count"] < hi],
                    artifact,
                    context,
                )
                for label, lo, hi in BUCKETS
            }
            metrics["diagnostics"] = {
                label: diagnostics([r for r in selected if r["watermarked"] == marked])
                for label, marked in (("clean", False), ("marked", True))
            }
            metrics["operating_point"] = asdict(artifact.operating_point)
            metrics["calibration_id"] = artifact.calibration_id
            metrics["usable_length_regime"] = [
                artifact.minimum_usable_tokens,
                artifact.maximum_usable_tokens,
            ]
            metrics["artifact"] = path.name
            metrics["calibration_distributions"] = {
                label: distribution(
                    [
                        r["visible_score"]
                        for r in calibration
                        if r["watermarked"] == marked and r["visible_score"] is not None
                    ]
                )
                for label, marked in (("clean", False), ("marked", True))
            }
            metrics["native_visible_threshold_disagreements"] = sum(
                (r["native_score"] > artifact.operating_point.empirical_threshold)
                != (r["visible_score"] > artifact.operating_point.empirical_threshold)
                for r in selected
                if r["native_score"] is not None and r["visible_score"] is not None
            )
            distribution_plot(evaluation, artifact, output / f"{name}-fpr-{alpha:g}.svg")
            metrics["performance"] = {
                label: {
                    field: distribution(
                        [
                            r[field]
                            for r in selected
                            if r["watermarked"] == marked and r[field] is not None
                        ]
                    )
                    for field in (
                        "generation_seconds",
                        "tokens_per_second",
                        "watermark_seconds",
                        "native_token_count",
                        "retokenized_token_count",
                        "usable_detector_token_count",
                    )
                }
                for label, marked in (("clean", False), ("marked", True))
            }
            # Curves are descriptive held-out score sweeps, never threshold tuning.
            scores = sorted(
                {r["visible_score"] for r in evaluation if r["visible_score"] is not None}
            )
            curve = []
            for threshold in scores:
                values = {}
                for label, marked in (("fpr", False), ("tpr", True)):
                    vals = [
                        r["visible_score"]
                        for r in evaluation
                        if r["watermarked"] == marked and r["visible_score"] is not None
                    ]
                    values[label] = sum(v > threshold for v in vals) / len(vals) if vals else None
                curve.append({"threshold": threshold, **values})
            metrics["roc_descriptive_all_scorable"] = curve
            if name == "kgw-z_score":
                metrics["legacy_z3"] = {
                    label: rate(
                        sum(
                            r["visible_score"] > 3
                            for r in evaluation
                            if r["watermarked"] == marked and r["visible_score"] is not None
                        ),
                        sum(
                            r["watermarked"] == marked and r["visible_score"] is not None
                            for r in evaluation
                        ),
                    )
                    for label, marked in (("fpr", False), ("tpr", True))
                }
            reports[f"{name}@{alpha:g}"] = metrics
    result = {
        "purpose": "detector_calibration",
        "reports": reports,
        "note": "TPR/FPR condition on non-abstained samples; yield includes all marked. "
        "Pooled FPR is not a conditional length guarantee; Wilson 95% intervals.",
    }
    write_json(output / "metrics.json", result)
    summary = [
        "# Experiment 002 detector calibration",
        "",
        result["note"],
        "",
        "| Detector | Target FPR | Threshold | Clean calibration n | Held-out TPR | "
        "Held-out FPR | Abstention |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, r in reports.items():
        op = r["operating_point"]
        summary.append(
            f"| {name} | {op['target_fpr']} | {op['empirical_threshold']:.6f} | "
            f"{op['number_of_clean_samples']} | {r['tpr']['value']} | "
            f"{r['fpr']['value']} | {r['abstention_rate']['value']} |"
        )
        summary.extend(["", *op["warnings"], ""])
    (output / "summary.md").write_text("\n".join(summary) + "\n", "utf-8")
    return result


def run_calibration(
    config_path: Path, *, output: Path | None = None, secrets_path: Path | None = None
) -> Path:
    config = CalibrationConfig.model_validate(yaml.safe_load(config_path.read_text("utf-8")))
    prompts, dataset_hash = load_prompts(config.dataset, config_path.parent)
    splits = split_prompts(prompts, config.calibration_count, config.evaluation_count, config.seed)
    output = output or Path("results") / config.name / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    )
    output.mkdir(parents=True, exist_ok=False)
    private = output / "private"
    private.mkdir(mode=0o700)
    keys = KeyStore.load(secrets_path) if secrets_path else KeyStore.create()
    keys.save(private / "secrets.json")
    resolved = config.model_dump()
    resolved["dataset"] = {"source": "jsonl", "path": "prompts.jsonl", "sample_count": len(prompts)}
    (output / "config.resolved.yaml").write_text(yaml.safe_dump(resolved), "utf-8")
    (output / "prompts.jsonl").write_text(
        "".join(canonical(asdict(p)) + "\n" for p in prompts), "utf-8"
    )
    split_data = {s: [asdict(p) for p in ps] for s, ps in splits.items()}
    write_json(output / "splits.json", {"seed": config.seed, "splits": split_data})
    model = load_model(config.model)
    try:
        schemes = {"kgw-z_score": KGWScheme(model, config.kgw, keys.derive("kgw", 0))}
        for depth in config.depths:
            for statistic in ("raw_mean", "weighted_mean"):
                cfg = config.synthid.model_copy(update={"depth": depth, "statistic": statistic})
                schemes[f"synthid-d{depth}-{statistic}"] = SynthIDScheme(
                    model, cfg, keys.derive("synthid", 0, depth)
                )
        contexts = {
            name: conditions(model, scheme, key_reference(keys, scheme.metadata()["scheme"], 0))
            for name, scheme in schemes.items()
        }
        manifest = {
            "version": 1,
            "dataset_sha256": dataset_hash,
            "split_seed": config.seed,
            "calibration_dataset_hash": hashlib.sha256(
                canonical(split_data["calibration"]).encode()
            ).hexdigest(),
            "evaluation_dataset_hash": hashlib.sha256(
                canonical(split_data["evaluation"]).encode()
            ).hexdigest(),
            "conditions": contexts,
            "target_fprs": config.target_fprs,
            "minimum_usable_tokens": config.minimum_usable_tokens,
            "environment": environment(),
            "started_at": datetime.now(UTC).isoformat(),
            "split_counts": {s: len(ps) for s, ps in splits.items()},
            "evaluation_authority": "visible_score",
            "completed": False,
        }
        write_json(output / "manifest.json", manifest)
        started = perf_counter()
        with (
            (output / "scores.jsonl").open("w", encoding="utf-8") as score_file,
            (private / "tokens.jsonl").open("w", encoding="utf-8") as tokens_file,
            (output / "samples.jsonl").open("w", encoding="utf-8") as samples_file,
        ):
            for split, selected in splits.items():
                for index, prompt in enumerate(selected):
                    seed = sample_seed(config.seed, prompt.id, 0) % (2**32 - 1)
                    generators = {"plain": None, "kgw": schemes["kgw-z_score"]}
                    generators.update(
                        {f"synthid-d{d}": schemes[f"synthid-d{d}-raw_mean"] for d in config.depths}
                    )
                    for generation_name, scheme in generators.items():
                        generated = model.generate(
                            prompt.text,
                            seed=seed,
                            watermark=(scheme.generation_config() if scheme else None),
                        )
                        sample_id = f"{split}-{prompt.id}-{generation_name}"
                        tokens_file.write(
                            canonical(
                                {
                                    "sample_id": sample_id,
                                    "token_ids": generated.token_ids,
                                    "prompt_token_ids": generated.prompt_token_ids,
                                }
                            )
                            + "\n"
                        )
                        samples_file.write(
                            canonical(
                                {
                                    "sample_id": sample_id,
                                    "prompt": prompt.text,
                                    "text": generated.text,
                                    "style": prompt.style,
                                }
                            )
                            + "\n"
                        )
                        for detector_id, detector in schemes.items():
                            family = (
                                "kgw"
                                if detector_id.startswith("kgw")
                                else detector_id.rsplit("-", 1)[0]
                            )
                            if generation_name != "plain" and family != generation_name:
                                continue
                            row = {
                                "sample_id": sample_id,
                                "prompt_id": prompt.id,
                                "style": prompt.style,
                                "split": split,
                                "seed": seed,
                                "watermarked": scheme is not None,
                                "detector_id": detector_id,
                                "generation_seconds": generated.seconds,
                                "watermark_seconds": generated.watermark_seconds,
                                "tokens_per_second": len(generated.token_ids) / generated.seconds,
                                **token_diagnostic(detector, generated, model),
                            }
                            score_file.write(canonical(row) + "\n")
                        score_file.flush()
                        samples_file.flush()
                        tokens_file.flush()
                        print(
                            f"{split} {index + 1}/{len(selected)} {generation_name}: "
                            f"{len(generated.token_ids)} tokens, {generated.seconds:.2f}s",
                            flush=True,
                        )
                if split == "calibration":
                    # Freeze before generating or inspecting any evaluation continuation.
                    summarize_run(output)
        manifest.update(completed=True, elapsed_seconds=perf_counter() - started)
        write_json(output / "manifest.json", manifest)
        summarize_run(output)
    finally:
        model.close()
    return output

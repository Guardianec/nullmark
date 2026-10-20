"""Descriptive statistics, with abstentions and failures kept visible."""

from statistics import mean, median, pstdev


def distribution(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": None, "median": None, "std": None, "min": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
        "std": pstdev(values),
        "min": ordered[0],
        "max": ordered[-1],
    }


def detection_metrics(rows: list[dict]) -> dict:
    valid = [r for r in rows if r["detection"]["prediction"] is not None]
    positive = [r for r in valid if r["watermarked"]]
    negative = [r for r in valid if not r["watermarked"]]
    tp = sum(r["detection"]["prediction"] for r in positive)
    fp = sum(r["detection"]["prediction"] for r in negative)
    return {
        "observations": len(rows),
        "valid": len(valid),
        "abstentions": len(rows) - len(valid),
        "watermarked": len(positive),
        "unwatermarked": len(negative),
        "true_positives": tp,
        "false_positives": fp,
        "true_positive_rate": tp / len(positive) if positive else None,
        "false_positive_rate": fp / len(negative) if negative else None,
        "accuracy": (tp + len(negative) - fp) / len(valid) if valid else None,
        "scores_watermarked": distribution([r["detection"]["score"] for r in positive]),
        "scores_unwatermarked": distribution([r["detection"]["score"] for r in negative]),
    }


def summarize(
    records: list[dict], evaluations: list[dict], failures: list[dict], runtime: float
) -> dict:
    return {
        "samples": len(records),
        "generation_failures": sum(f["stage"] == "generation" for f in failures),
        "detection_failures": sum(f["stage"] == "detection" for f in failures),
        "runtime_seconds": runtime,
        "token_lengths": distribution([r["token_count"] for r in records]),
        "generation_seconds": distribution([r["generation_seconds"] for r in records]),
        "roundtrip_mismatches": sum(not r["text_roundtrip_exact"] for r in records),
        "detectors": {
            name: {
                **detection_metrics([r for r in evaluations if r["detector"] == name]),
                "by_key": {
                    str(index): detection_metrics(
                        [
                            r
                            for r in evaluations
                            if r["detector"] == name and r["key_index"] == index
                        ]
                    )
                    for index in sorted(
                        {r["key_index"] for r in evaluations if r["detector"] == name}
                    )
                },
            }
            for name in ("synthid", "kgw")
        },
    }


def summary_markdown(metrics: dict, purpose: str) -> str:
    def rate(value):
        return "n/a" if value is None else f"{value:.1%}"

    lines = [
        f"# NullMark v0.1.0 — {purpose} results",
        "",
        "Small runs are descriptive checks, not research-scale evidence.",
        "",
        f"Samples: {metrics['samples']}; generation failures: {metrics['generation_failures']}; "
        f"detection failures: {metrics['detection_failures']}; "
        f"runtime: {metrics['runtime_seconds']:.2f}s.",
        "",
        "| Detector | TPR | FPR | Accuracy | Abstentions |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name, data in metrics["detectors"].items():
        lines.append(
            f"| {name} | {rate(data['true_positive_rate'])} | "
            f"{rate(data['false_positive_rate'])} | "
            f"{rate(data['accuracy'])} | {data['abstentions']} |"
        )
    lines += [
        "",
        "SynthID uses an uncalibrated mean-g threshold; KGW p-values use a normal approximation.",
        "Rates exclude abstentions and failed detections. Controls are paired across detectors; "
        "observations are not independent replicates.",
        "Detection retokenizes continuation text only. See raw JSONL and per-key metrics.",
        "",
    ]
    return "\n".join(lines)

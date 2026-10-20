"""Evasion accounting keeps failures and abstentions in eligible denominators."""

import math
from collections import defaultdict
from statistics import mean


def outcome(before, after=None, *, failure=False):
    if before["state"] != "DETECTED":
        return "BASELINE MISS" if before["state"] == "NOT DETECTED" else "BASELINE ABSTENTION"
    if failure:
        return "ATTACK FAILURE"
    return {
        "DETECTED": "DETECTED",
        "NOT DETECTED": "EVASION",
        "INSUFFICIENT EVIDENCE": "ABSTENTION",
    }[after["state"]]


def distribution(values):
    values = sorted(v for v in values if v is not None and math.isfinite(v))
    if not values:
        return {"count": 0, "mean": None}
    return {
        "count": len(values),
        "mean": mean(values),
        **{
            f"p{p:02}": values[max(0, math.ceil(p / 100 * len(values)) - 1)]
            for p in (5, 25, 50, 75, 95)
        },
    }


def aggregate(baselines, rows):
    baseline_summary = {}
    for scheme in sorted({r["scheme"] for r in baselines}):
        selected = [r for r in baselines if r["scheme"] == scheme]
        n = len(selected)
        baseline_summary[scheme] = {
            "total": n,
            **{
                name: {
                    "count": sum(r["before"]["state"] == state for r in selected),
                    "rate": sum(r["before"]["state"] == state for r in selected) / n,
                }
                for name, state in (
                    ("eligible", "DETECTED"),
                    ("miss", "NOT DETECTED"),
                    ("abstention", "INSUFFICIENT EVIDENCE"),
                )
            },
        }
    groups = defaultdict(list)
    for row in rows:
        if row["before"]["state"] == "DETECTED":
            groups[(row["scheme"], row["attack"], row["budget"])].append(row)
    results = []
    for (scheme, attack, budget), group in groups.items():
        n = len(group)
        success = [r for r in group if r["outcome"] != "ATTACK FAILURE"]
        quality = [r["quality"] for r in success]
        counts = {
            state: sum(r["outcome"] == state for r in group)
            for state in ("EVASION", "DETECTED", "ABSTENTION", "ATTACK FAILURE")
        }
        conditioned = {}
        for threshold in (0.90, 0.95):
            subset = [
                r
                for r in success
                if r["quality"]["semantic_similarity"] is not None
                and r["quality"]["semantic_similarity"] >= threshold
            ]
            numerator = sum(r["outcome"] == "EVASION" for r in subset)
            conditioned[str(threshold)] = {
                "numerator": numerator,
                "denominator": len(subset),
                "rate": numerator / len(subset) if subset else None,
                "coverage_of_eligible": len(subset) / n,
            }
        results.append(
            {
                "scheme": scheme,
                "attack": attack,
                "budget": budget,
                "eligible_baselines": n,
                "counts": counts,
                "completion_rate": len(success) / n,
                "evasion_rate": counts["EVASION"] / n,
                "detection_rate": counts["DETECTED"] / n,
                "abstention_rate": counts["ABSTENTION"] / n,
                "quality_conditioned": conditioned,
                "distributions": {
                    **{
                        name: distribution(q[name] for q in quality)
                        for name in (
                            "semantic_similarity",
                            "word_edit_fraction",
                            "token_edit_fraction",
                            "length_ratio",
                            "lexical_similarity",
                            "anchor_preservation",
                        )
                    },
                    "score_before": distribution(r["before"]["score"] for r in group),
                    "score_after": distribution(r["after"]["score"] for r in success),
                    "score_reduction": distribution(
                        r["before"]["score"] - r["after"]["score"]
                        for r in success
                        if r["after"]["score"] is not None
                    ),
                    "runtime_seconds": distribution(r["runtime_seconds"] for r in group),
                },
            }
        )
    return {
        "baseline": baseline_summary,
        "groups": results,
        "denominator_note": "All eligible attempts, including failures and abstentions. "
        "Quality-conditioned rates use the explicitly reported passing subset.",
    }

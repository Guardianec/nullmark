"""Trusted post-hoc analysis. These results never enter the blind worker."""

import csv
from statistics import mean

import numpy as np

from nullmark.attacks.skd import BUDGETS, FEATURES, METHODS
from nullmark.evaluation.attack_metrics import aggregate
from nullmark.experiments.runner import read_jsonl, write_json
from nullmark.experiments.skd import public_id

BOOTSTRAP_SEED = 20261024
BOOTSTRAP_COUNT = 5000


def paired_bootstrap(differences, *, seed=BOOTSTRAP_SEED, count=BOOTSTRAP_COUNT):
    if not differences:
        return {"n": 0, "mean": None, "lower": None, "upper": None}
    values = np.asarray(differences, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ValueError("nonfinite paired difference")
    rng = np.random.default_rng(seed)
    estimates = np.array([np.mean(rng.choice(values, len(values))) for _ in range(count)])
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "lower": float(np.quantile(estimates, 0.025)),
        "upper": float(np.quantile(estimates, 0.975)),
    }


def ranks(values):
    return np.array(
        [sum(x < v for x in values) + (sum(x == v for x in values) - 1) / 2 for v in values],
        dtype=float,
    )


def spearman(x, y):
    a, b = ranks(x), ranks(y)
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def comparable(rows, pools, k):
    grouped = {}
    for row in rows:
        if row["budget"] == k:
            grouped.setdefault(row["sample_id"], {})[row["attack"]] = row
    return {
        sid
        for sid, methods in grouped.items()
        if pools.get(public_id(sid), {}).get("coverage", {}).get("selectable", 0) >= k
        and set(methods) == set(METHODS)
        and all(not r["failure"] and r["skd"]["actual_edits"] == k for r in methods.values())
    }


def analyze(baselines, rows, pools):
    coverage, paired, correlations, diagnostics, matched = [], [], [], [], []
    pool_by_id = {p["sample_id"]: p for p in pools}
    for scheme in sorted({b["scheme"] for b in baselines}):
        eligible = [
            b for b in baselines if b["scheme"] == scheme and b["before"]["state"] == "DETECTED"
        ]
        scheme_rows = [r for r in rows if r["scheme"] == scheme]
        for k in BUDGETS:
            available = sum(
                pool_by_id.get(public_id(b["sample_id"]), {})
                .get("coverage", {})
                .get("selectable", 0)
                >= k
                for b in eligible
            )
            ids = comparable(scheme_rows, pool_by_id, k)
            coverage.append(
                {
                    "scheme": scheme,
                    "k": k,
                    "eligible": len(eligible),
                    "pool_capable": available,
                    "rate": available / len(eligible) if eligible else None,
                    "all_selectors_exact_k": len(ids),
                    "missing_pool": sum(
                        public_id(b["sample_id"]) not in pool_by_id for b in eligible
                    ),
                }
            )
            subset = [r for r in scheme_rows if r["sample_id"] in ids and r["budget"] == k]
            matched.extend(aggregate(eligible, subset)["groups"])
            indexed = {(r["sample_id"], r["attack"]): r for r in subset}
            for baseline_method in ("random_pool", "entropy_only"):
                differences = []
                for sid in sorted(ids):
                    full, reference = indexed[(sid, "skd")], indexed[(sid, baseline_method)]
                    if (
                        full["after"]["score"] is not None
                        and reference["after"]["score"] is not None
                    ):
                        differences.append(reference["after"]["score"] - full["after"]["score"])
                paired.append(
                    {
                        "scheme": scheme,
                        "k": k,
                        "reference": baseline_method,
                        "comparable_samples": len(ids),
                        "missing_score_pairs": len(ids) - len(differences),
                        **paired_bootstrap(differences),
                    }
                )
            for method in METHODS:
                selected_rows = [r for r in subset if r["attack"] == method]
                selected = []
                for r in selected_rows:
                    pool = pool_by_id[public_id(r["sample_id"])]
                    selected += [
                        c
                        for c in pool["candidates"]
                        if c["candidate_id"] in r["skd"]["selected_ids"]
                    ]
                diagnostics.append(
                    {
                        "scheme": scheme,
                        "k": k,
                        "method": method,
                        "samples": len(selected_rows),
                        "candidates": len(selected),
                        **{
                            f: mean(c["normalized_" + f] for c in selected) if selected else None
                            for f in FEATURES
                        },
                        "local_semantic_similarity": mean(
                            c["local_semantic_similarity"] for c in selected
                        )
                        if selected
                        else None,
                    }
                )
            # Candidate effect is observable without interaction only at k=1.
            if k == 1:
                seen, observations = set(), []
                for r in subset:
                    if r["after"]["score"] is None:
                        continue
                    cid = r["skd"]["selected_ids"][0]
                    identity = (r["sample_id"], cid)
                    if identity in seen:
                        continue
                    seen.add(identity)
                    c = next(
                        c
                        for c in pool_by_id[public_id(r["sample_id"])]["candidates"]
                        if c["candidate_id"] == cid
                    )
                    observations.append((c, r["before"]["score"] - r["after"]["score"]))
                correlations += [
                    {
                        "scheme": scheme,
                        "feature": f,
                        "n": len(observations),
                        "spearman": spearman(
                            [c[f] for c, _ in observations], [v for _, v in observations]
                        ),
                    }
                    for f in FEATURES
                ]
    return {
        "coverage": coverage,
        "paired": paired,
        "diagnostics": diagnostics,
        "matched_groups": matched,
        "correlations": correlations,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_count": BOOTSTRAP_COUNT,
        "note": "Positive paired difference favors SKD. Exact-k subset requires all selectors. "
        "Correlations deduplicate selected one-edit candidates; samples can contribute multiple "
        "candidates, so these are descriptive, dependent observations, not causal estimates.",
    }


def report(output, metrics, baselines, rows):
    pools = read_jsonl(output / "candidates/candidates.jsonl")
    analysis = analyze(baselines, rows, pools)
    write_json(output / "ablations.json", analysis)
    write_json(output / "correlations.json", analysis["correlations"])
    lines = [
        "# Experiment 004 — Sparse Keyless Disruption",
        "",
        "Fixed 1/2/3/5 local edits; one candidate pool per sample. All weights were committed "
        "before detector evaluation. Positive score reduction means weaker detector evidence.",
        "",
        "Target FPR 1%; the frozen SynthID d20 weighted evaluator had observed held-out FPR "
        "3/99 (3.03%). No recalibration. Embedding cosine does not establish factual correctness.",
        "",
        "## Baseline eligibility",
        "",
    ]
    for scheme, value in metrics["baseline"].items():
        lines.append(
            f"- {scheme}: {value['eligible']['count']}/{value['total']} eligible; "
            f"miss {value['miss']['count']}; abstention {value['abstention']['count']}."
        )
    lines += [
        "",
        "## Candidate coverage among eligible baselines",
        "",
        "|Scheme|Edits|Pool capable / eligible|All selectors exact k|Missing pool|",
        "|---|---:|---:|---:|---:|",
    ]
    for r in analysis["coverage"]:
        lines.append(
            f"|{r['scheme']}|{r['k']}|{r['pool_capable']}/{r['eligible']}|"
            f"{r['all_selectors_exact_k']}|{r['missing_pool']}|"
        )

    def number(value):
        return "n/a" if value is None else f"{value:.4f}"

    for title, groups in (
        ("All eligible attempts (exhaustion retained)", metrics["groups"]),
        ("Exact-k comparable subsets", analysis["matched_groups"]),
    ):
        lines += [
            "",
            "## " + title,
            "",
            "|Scheme|Method|k|N|Evasion|Abstention|Failures|Δ score|Semantic|"
            "Word fraction|Token fraction|Anchors|",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in groups:
            d = r["distributions"]
            lines.append(
                f"|{r['scheme']}|{r['attack']}|{r['budget']}|{r['eligible_baselines']}|"
                f"{r['evasion_rate']:.2%}|{r['abstention_rate']:.2%}|"
                f"{r['counts']['ATTACK FAILURE']}|"
                + "|".join(
                    number(d[f]["mean"])
                    for f in (
                        "score_reduction",
                        "semantic_similarity",
                        "word_edit_fraction",
                        "token_edit_fraction",
                        "anchor_preservation",
                    )
                )
                + "|"
            )
    lines += [
        "",
        "## Paired score-reduction differences, percentile bootstrap 95% CI",
        "",
        "|Scheme|k|Reference|Pairs|SKD minus reference|95% interval|",
        "|---|---:|---|---:|---:|---|",
    ]
    for r in analysis["paired"]:
        lines.append(
            f"|{r['scheme']}|{r['k']}|{r['reference']}|{r['n']}|{number(r['mean'])}|"
            f"[{number(r['lower'])}, {number(r['upper'])}]|"
        )
    lines += [
        "",
        "## Limits",
        "",
        metrics["denominator_note"],
        "",
        analysis["note"],
        "",
        "Candidate coverage is measured on eligible baselines; ineligible samples are reported "
        "separately. Failed pools count as unavailable. Candidate-local semantic checks can miss "
        "factual drift. Shared feature signals may be correlated. Multi-edit combinations are "
        "validated structurally, with whole-text quality measured after finalization. Historical "
        "v0.2 denominators are separate. This experiment makes no cross-key or cross-scheme "
        "transfer claims. See quality.jsonl and metrics.json for "
        ".90/.95 quality-conditioned rates.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), "utf-8")
    with (output / "pareto.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_id",
                "scheme",
                "method",
                "k",
                "actual_edits",
                "outcome",
                "score_reduction",
                "semantic_similarity",
                "word_edit_fraction",
                "token_edit_fraction",
            ]
        )
        for r in rows:
            q = r.get("quality", {})
            drop = (
                r["before"]["score"] - r["after"]["score"]
                if r["after"] and r["after"]["score"] is not None
                else None
            )
            writer.writerow(
                [
                    r["sample_id"],
                    r["scheme"],
                    r["attack"],
                    r["budget"],
                    r.get("skd", {}).get("actual_edits"),
                    r["outcome"],
                    drop,
                    *[
                        q.get(f)
                        for f in (
                            "semantic_similarity",
                            "word_edit_fraction",
                            "token_edit_fraction",
                        )
                    ],
                ]
            )
    plots(output, analysis)


def plots(output, analysis):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    destination = output / "plots"
    destination.mkdir(exist_ok=True)
    for metric, label in (
        ("score_reduction", "Mean detector score reduction"),
        ("evasion_rate", "Evasion rate"),
        ("semantic_similarity", "Embedding cosine"),
        ("quality_conditioned", "Evasion among cosine ≥ .95"),
    ):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        for axis, scheme in zip(axes, ("kgw", "synthid"), strict=True):
            for method in METHODS:
                group = sorted(
                    [
                        r
                        for r in analysis["matched_groups"]
                        if r["scheme"] == scheme and r["attack"] == method
                    ],
                    key=lambda r: r["budget"],
                )
                values = [
                    r["evasion_rate"]
                    if metric == "evasion_rate"
                    else r["quality_conditioned"]["0.95"]["rate"]
                    if metric == "quality_conditioned"
                    else r["distributions"][metric]["mean"]
                    for r in group
                ]
                axis.plot([r["budget"] for r in group], values, marker="o", label=method)
            axis.set(title=scheme, xlabel="Exact localized edits", ylabel=label, xticks=BUDGETS)
            axis.grid(alpha=0.2)
        axes[-1].legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(destination / f"{metric}.png", dpi=150)
        plt.close(fig)
    fig, axis = plt.subplots(figsize=(7, 4))
    for scheme in ("kgw", "synthid"):
        group = [r for r in analysis["coverage"] if r["scheme"] == scheme]
        axis.plot([r["k"] for r in group], [r["rate"] for r in group], marker="o", label=scheme)
    axis.set(
        xlabel="Selectable non-overlapping edits ≥ k",
        ylabel="Fraction of eligible baselines",
        xticks=BUDGETS,
        ylim=(0, 1.05),
    )
    axis.legend()
    fig.tight_layout()
    fig.savefig(destination / "candidate_coverage.png", dpi=150)
    plt.close(fig)
    for reference in ("random_pool", "entropy_only"):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for axis, scheme in zip(axes, ("kgw", "synthid"), strict=True):
            group = [
                r
                for r in analysis["paired"]
                if r["scheme"] == scheme and r["reference"] == reference and r["n"]
            ]
            axis.errorbar(
                [r["k"] for r in group],
                [r["mean"] for r in group],
                yerr=[
                    [r["mean"] - r["lower"] for r in group],
                    [r["upper"] - r["mean"] for r in group],
                ],
                fmt="o",
            )
            axis.axhline(0, color="grey", linewidth=1)
            axis.set(
                title=scheme,
                xlabel="Exact edits",
                ylabel="SKD minus reference score reduction",
                xticks=BUDGETS,
            )
        fig.tight_layout()
        fig.savefig(destination / f"paired_{reference}.png", dpi=150)
        plt.close(fig)

"""Static research plots and transparent descriptive tables from measured rows."""

import csv
from pathlib import Path

from nullmark.experiments.runner import read_jsonl


def report(output: Path, metrics):
    rows = metrics["groups"]
    lines = [
        "# Experiment 003 — Baseline Attack Benchmark",
        "",
        metrics["denominator_note"],
        "",
        "One local Qwen model, one master/key configuration, a fresh prompt corpus and "
        "frozen v0.1.1 evaluators. Target FPR 1%; SynthID d20 weighted observed held-out "
        "FPR was 3/99 (3.03%). No calibration was fitted on this corpus.",
        "",
        "Embedding cosine is semantic similarity, not factual correctness. "
        "The .90/.95 bands are descriptive operating points, not universal thresholds.",
        "",
        "## Baseline eligibility",
        "",
    ]
    for scheme, value in metrics["baseline"].items():
        lines.append(
            f"- {scheme}: {value['eligible']['count']}/{value['total']} eligible "
            f"({value['eligible']['rate']:.1%}); miss {value['miss']['rate']:.1%}; "
            f"abstention {value['abstention']['rate']:.1%}."
        )
    lines += [
        "",
        "## Attack outcomes",
        "",
        "|Scheme|Attack|Budget|Eligible|Complete|Evasion|Abstain|Δ score|Semantic|Word edit|",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def number(value):
        return "n/a" if value is None else f"{value:.3f}"

    for row in rows:
        d = row["distributions"]
        lines.append(
            f"|{row['scheme']}|{row['attack']}|{row['budget']}|"
            f"{row['eligible_baselines']}|{row['completion_rate']:.1%}|"
            f"{row['evasion_rate']:.1%}|{row['abstention_rate']:.1%}|"
            f"{number(d['score_reduction']['mean'])}|"
            f"{number(d['semantic_similarity']['mean'])}|"
            f"{number(d['word_edit_fraction']['mean'])}|"
        )
    lines += [
        "",
        "## Quality-conditioned evasion",
        "",
        "|Scheme|Attack|Budget|Semantic band|Evasions / passing samples|Coverage|",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        for threshold, band in row["quality_conditioned"].items():
            lines.append(
                f"|{row['scheme']}|{row['attack']}|{row['budget']}|≥{threshold}|"
                f"{band['numerator']}/{band['denominator']}|"
                f"{band['coverage_of_eligible']:.1%}|"
            )
    lines += ["", "## Interpretation", ""]
    for scheme in metrics["baseline"]:
        subset = [r for r in rows if r["scheme"] == scheme]
        if subset:
            best = max(subset, key=lambda r: r["evasion_rate"])
            preserving = max(
                subset,
                key=lambda r: r["distributions"]["semantic_similarity"]["mean"]
                if r["distributions"]["semantic_similarity"]["mean"] is not None
                else -1,
            )
            lines.append(
                f"- {scheme}: largest measured evasion is {best['attack']} "
                f"at budget {best['budget']} ({best['evasion_rate']:.1%}); highest "
                f"mean semantic similarity is {preserving['attack']} "
                f"at budget {preserving['budget']}. Compare actual edits, failures and "
                "quality bands before interpreting this ordering."
            )
            strongest = max(
                subset,
                key=lambda r: r["distributions"]["score_reduction"]["mean"]
                if r["distributions"]["score_reduction"]["mean"] is not None
                else -1e9,
            )
            lines.append(
                f"- {scheme}: largest paired mean score reduction is "
                f"{strongest['attack']} at {strongest['budget']}: "
                f"{number(strongest['distributions']['score_reduction']['mean'])}. "
                "This is a within-scheme comparison only."
            )
            observed = sorted(
                r["budget"] for r in subset if r["budget"] is not None and r["evasion_rate"] > 0
            )
            lines.append(
                f"- {scheme}: sparse requested budgets with at least one observed "
                f"evasion: {sorted(set(observed)) or 'none'}. This is a fixed sweep, "
                "not an estimate of the minimum successful edit budget."
            )
            for budget in (0.01, 0.02, 0.05, 0.1, 0.2):
                pair = {r["attack"]: r for r in subset if r["budget"] == budget}
                if {"entropy_rewrite", "random_edit"} <= pair.keys():
                    entropy, random = pair["entropy_rewrite"], pair["random_edit"]
                    lines.append(
                        f"- {scheme}, requested {budget:.0%}: entropy evasion "
                        f"{entropy['evasion_rate']:.1%}, random {random['evasion_rate']:.1%}; "
                        "mean actual word edits "
                        f"{number(entropy['distributions']['word_edit_fraction']['mean'])} "
                        f"vs {number(random['distributions']['word_edit_fraction']['mean'])}. "
                        "Different candidate availability prevents attributing the whole "
                        "difference to position selection alone."
                    )
    lines += [
        "",
        "Score units differ between KGW and SynthID; compare within each scheme. "
        "Sparse budgets are upper bounds: safe candidates can run out. "
        "Abstention is not evasion. Failures remain in all-eligible denominators. "
        "No minimum successful budget search was performed. Human inspection is "
        "required for factual drift, grammar and truncated source generations.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), "utf-8")
    evaluation = read_jsonl(output / "evaluation.jsonl")
    with (output / "pareto.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sample_id",
                "scheme",
                "attack",
                "budget",
                "outcome",
                "semantic_similarity",
                "word_edit_fraction",
                "token_edit_fraction",
                "score_reduction",
            ]
        )
        for r in evaluation:
            q = r.get("quality", {})
            writer.writerow(
                [
                    r["sample_id"],
                    r["scheme"],
                    r["attack"],
                    r["budget"],
                    r["outcome"],
                    q.get("semantic_similarity"),
                    q.get("word_edit_fraction"),
                    q.get("token_edit_fraction"),
                    r["before"]["score"] - r["after"]["score"]
                    if r["after"] and r["after"]["score"] is not None
                    else None,
                ]
            )
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import PercentFormatter
    except ImportError:
        raise ValueError("Static plots require nullmark[evaluation]") from None
    plots = output / "plots"
    plots.mkdir(exist_ok=True)
    for name, ylabel in (
        ("evasion_rate", "Evasion / all eligible"),
        ("score_reduction", "Mean detector score reduction"),
        ("semantic_similarity", "Mean semantic similarity"),
    ):
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
        for ax, scheme in zip(axes, sorted(metrics["baseline"]), strict=True):
            for attack in sorted({r["attack"] for r in rows}):
                selected = [
                    r
                    for r in rows
                    if r["scheme"] == scheme and r["attack"] == attack and r["budget"] is not None
                ]
                if not selected:
                    continue
                ax.plot(
                    [r["budget"] * 100 for r in selected],
                    [
                        r[name] if name == "evasion_rate" else r["distributions"][name]["mean"]
                        for r in selected
                    ],
                    marker="o",
                    label=attack,
                )
            ax.set(xlabel="Requested word edit budget (%)", ylabel=ylabel, title=scheme)
            ax.set_xticks([1, 2, 5, 10, 20])
            if name == "evasion_rate":
                ax.set_ylim(
                    0, min(1, max(0.1, max((r["evasion_rate"] for r in rows), default=0) * 1.15))
                )
                ax.yaxis.set_major_formatter(PercentFormatter(1))
            ax.legend(fontsize=8)
            ax.grid(alpha=0.2)
        fig.savefig(plots / f"{name}.svg")
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for ax, scheme in zip(axes, sorted(metrics["baseline"]), strict=True):
        for attack in sorted({r["attack"] for r in rows}):
            selected = [
                r
                for r in evaluation
                if r["scheme"] == scheme
                and r["attack"] == attack
                and r.get("quality", {}).get("semantic_similarity") is not None
                and r["after"]["score"] is not None
            ]
            ax.scatter(
                [r["quality"]["semantic_similarity"] for r in selected],
                [r["after"]["score"] for r in selected],
                alpha=0.35,
                s=12,
                label=attack,
            )
        ax.set(xlabel="Semantic similarity", ylabel="Post-attack score", title=scheme)
        ax.legend(fontsize=8)
    fig.savefig(plots / "semantic-vs-score.svg")
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained", sharex=True, sharey=True)
    for ax, scheme in zip(axes, sorted(metrics["baseline"]), strict=True):
        for attack in sorted({r["attack"] for r in rows}):
            selected = [
                r
                for r in rows
                if r["scheme"] == scheme
                and r["attack"] == attack
                and r["distributions"]["word_edit_fraction"]["mean"] is not None
            ]
            ax.plot(
                [r["distributions"]["word_edit_fraction"]["mean"] * 100 for r in selected],
                [r["evasion_rate"] for r in selected],
                marker="o",
                label=attack,
            )
        ax.set(
            xlabel="Mean actual word edit fraction, completed attacks (%)",
            ylabel="Evasion / all eligible attempts",
            title=scheme,
        )
        ax.set_ylim(0, min(1, max(0.1, max((r["evasion_rate"] for r in rows), default=0) * 1.15)))
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.legend(fontsize=8)
        ax.grid(alpha=0.2)
    fig.savefig(plots / "actual-edit-vs-evasion.svg")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 4), layout="constrained")
    for scheme in sorted(metrics["baseline"]):
        for threshold in ("0.9", "0.95"):
            selected = [r for r in rows if r["scheme"] == scheme]
            ax.plot(
                range(len(selected)),
                [r["quality_conditioned"][threshold]["rate"] for r in selected],
                marker="o",
                label=f"{scheme} cosine ≥ {threshold}",
            )
    ax.set_xticks(
        range(len(selected)),
        [
            f"{r['attack']}\n{r['budget'] if r['budget'] is not None else 'actual'}"
            for r in selected
        ],
        rotation=65,
        ha="right",
        fontsize=7,
    )
    ax.set(ylabel="Evasion / passing quality subset")
    conditional = [
        band["rate"]
        for r in rows
        for band in r["quality_conditioned"].values()
        if band["rate"] is not None
    ]
    ax.set_ylim(0, min(1, max(0.1, max(conditional, default=0) * 1.15)))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(fontsize=8)
    fig.savefig(plots / "quality-conditioned.svg")
    plt.close(fig)

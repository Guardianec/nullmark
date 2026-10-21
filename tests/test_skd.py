import io
import json
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from nullmark.attacks.base import AttackInput
from nullmark.attacks.model import TransformationModel
from nullmark.attacks.skd import (
    BUDGETS,
    FEATURES,
    METHODS,
    apply,
    capacity,
    context_leverage,
    generate_pool,
    local_pair,
    normalize,
    parse_proposals,
    select,
    settings,
    transform,
    validate_candidate,
)
from nullmark.config import DatasetConfig
from nullmark.datasets import load_prompts
from nullmark.experiments.attacks import validate_disjoint
from nullmark.experiments.skd_report import analyze, paired_bootstrap, spearman

TEXT = "The useful method often helps people quickly understand important changes."


def proposal(word="useful", replacement="helpful", text=TEXT):
    start = text.index(word)
    return dict(start=start, end=start + len(word), original=word, replacement=replacement)


class Model:
    digest = "a" * 64
    sampling = {"temperature": 0.2}
    calls = 0

    def tokenize(self, text):
        return list(text.encode())

    def complete(self, instruction, seed):
        self.calls += 1
        return json.dumps([proposal(), proposal("method", "approach"), proposal()])

    def skd_entropies(self, text, pool):
        return {(c["start"], c["end"]): c["start"] / 100 for c in pool}


def pool():
    return generate_pool(
        AttackInput("opaque", "p", TEXT),
        Model(),
        SimpleNamespace(compare=lambda a, b: 0.97),
        settings(),
        7,
    )


def test_validation_exact_offsets_and_identity():
    a = validate_candidate(TEXT, proposal(), settings())
    assert a == validate_candidate(TEXT, proposal(), settings())
    assert len(a["candidate_id"]) == len(a["result_sha256"]) == 64


@pytest.mark.parametrize(
    "update",
    [
        {"start": True},
        {"end": 2000},
        {"start": -1},
        {"original": "wrong"},
        {"replacement": ""},
        {"replacement": "useful"},
        {"replacement": "not helpful"},
        {"replacement": "Alice"},
        {"replacement": "helpful. A new sentence"},
        {"replacement": "here is my replacement"},
        {"replacement": "x y z a b c d"},
        {"key_ref": "private"},
        {"replacement": "helpful 2026"},
    ],
)
def test_invalid_candidate_rejected(update):
    with pytest.raises(ValueError):
        validate_candidate(TEXT, {**proposal(), **update}, settings())


@pytest.mark.parametrize(
    "text,word",
    [
        ('The "useful method" helps.', "useful"),
        ("The `useful` method helps.", "useful"),
        ("Alice helps people.", "Alice"),
        ("The method is not useful.", "not"),
        ("https://useful.example helps.", "useful"),
        ("The formula = useful + other", "useful"),
        ("The useful@example.org mailbox", "useful"),
        ("The 2026 method helps", "2026"),
        ("The useful or helpful method", "or"),
        ("The high-speed mechanism", "speed"),
    ],
)
def test_protected_anchors(text, word):
    with pytest.raises(ValueError):
        validate_candidate(text, proposal(word, "helpful", text), settings())


@pytest.mark.parametrize("raw", ["{}", "```json\n[]\n```", "Here is []", "[", "null"])
def test_strict_json(raw):
    with pytest.raises(ValueError):
        parse_proposals(raw)


def test_pool_dedup_features_and_coverage():
    artifact = pool()
    assert artifact["coverage"] == dict(
        source_words=10, proposed=9, proposed_spans=9, valid=9, safe=9, unique=2, selectable=2
    )
    assert all(set(FEATURES) <= c.keys() for c in artifact["candidates"])
    c = artifact["candidates"][0]
    assert c["R"] == 0.5 and c["D"] == pytest.approx(0.03)
    assert c["local_semantic_similarity"] == 0.97
    forbidden = {
        "key",
        "key_ref",
        "threshold",
        "detector_score",
        "g_values",
        "greenlist",
        "native_token_ids",
        "calibration_path",
    }

    def inspect(value):
        if isinstance(value, dict):
            assert not forbidden & value.keys()
            for x in value.values():
                inspect(x)
        elif isinstance(value, list):
            for x in value:
                inspect(x)

    inspect(artifact)


def test_semantic_filter_and_empty_malformed_batches():
    source = AttackInput("x", "p", TEXT)
    artifact = generate_pool(
        source, Model(), SimpleNamespace(compare=lambda a, b: 0.84), settings(), 7
    )
    assert artifact["coverage"]["safe"] == 0 and artifact["candidates"] == []
    model = Model()
    model.complete = lambda *a: "bad JSON"
    artifact = generate_pool(source, model, None, settings(), 7)
    assert artifact["rejections"]["malformed_batch"] == 3


def test_feature_orderings_and_local_window():
    assert context_leverage([1, 2, 3, 4, 5], [1, 8, 3, 4, 5], 2) == 2
    assert context_leverage([1, 2, 3], [1, 2, 3], 8) == 0
    assert context_leverage([1, 2, 3, 4], [1, 9, 10, 3, 4], 8) > 0
    a, b = local_pair(TEXT, proposal(), 1)
    assert a == "The useful method" and b == "The helpful method"
    artifact = pool()
    by_word = {c["original"]: c for c in artifact["candidates"]}
    assert by_word["method"]["E"] > by_word["useful"]["E"]
    assert all(c["T"] > 0 for c in artifact["candidates"])


def test_ordinary_entropy_span_aggregation():
    model = TransformationModel.__new__(TransformationModel)
    model.sampling = {"context_length": 100}
    model.tokenize = lambda text: list(text.encode())
    model.llm = SimpleNamespace(
        reset=lambda: None,
        eval=lambda x: None,
        detokenize=lambda ids: bytes(ids),
        scores=np.array([[0.0, 0.0], [20.0, -20.0], [0.0, 0.0]]),
    )
    entropy = model.skd_entropies("abc", [{"start": 1, "end": 2}, {"start": 1, "end": 3}])
    assert entropy[(1, 2)] == pytest.approx(np.log(2))
    assert entropy[(1, 3)] == pytest.approx(np.log(2) / 2)


def test_normalization_ties_weights_and_missing():
    values = [{f: v for f in FEATURES} for v in [1.0, 1.0, 3.0]]
    normalize(values, settings()["weights"])
    assert [r["normalized_E"] for r in values] == [0.25, 0.25, 1.0]
    assert values[-1]["final_score"] == pytest.approx(2.75)
    single = [{f: 1.0 for f in FEATURES}]
    normalize(single, settings()["weights"])
    assert single[0]["normalized_D"] == 0.5
    with pytest.raises(ValueError):
        normalize([{f: float("nan") for f in FEATURES}], settings()["weights"])
    with pytest.raises(KeyError):
        normalize([{}], settings()["weights"])
    with pytest.raises(ValueError):
        settings({"weights": {f: float("inf") for f in FEATURES}})


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("k", BUDGETS)
def test_selectors_same_pool_exhaustion_and_determinism(method, k):
    artifact = pool()
    before = json.dumps(artifact, sort_keys=True)
    a = transform(
        AttackInput("x", "p", TEXT), method=method, k=k, seed=9, model=Model(), artifact=artifact
    )
    b = transform(
        AttackInput("x", "p", TEXT), method=method, k=k, seed=9, model=Model(), artifact=artifact
    )
    assert a.text == b.text
    assert a.skd["actual_edits"] == min(k, 2)
    assert a.skd["candidate_exhaustion"] == (k > 2)
    assert a.skd["pool_sha256"] == artifact["pool_sha256"]
    assert json.dumps(artifact, sort_keys=True) == before
    assert len(a.skd["selected_ids"]) == min(k, 2)


def test_exact_k_feasibility_and_right_to_left():
    candidates = [
        dict(
            start=a,
            end=b,
            candidate_id=str(i),
            original=TEXT[a:b],
            replacement="x",
            final_score=score,
        )
        for i, (a, b, score) in enumerate([(4, 17, 9), (4, 10, 2), (11, 17, 1)])
    ]
    assert capacity(candidates) == 2
    chosen = select(candidates, "skd", 2, 0)
    assert [c["candidate_id"] for c in chosen] == ["1", "2"]
    assert apply(TEXT, chosen).startswith("The x x often")
    with pytest.raises(ValueError):
        apply(TEXT, candidates)
    assert select([], "skd", 5, 7) == []


def test_corpus_disjointness():
    base = Path("configs/benchmarks")
    prompts, _ = load_prompts(
        DatasetConfig(source="jsonl", path="skd-v1.jsonl", sample_count=240), base
    )
    assert len(prompts) == 240 and len({p.style for p in prompts}) == 8
    for path in (
        base / "attacks-v1.jsonl",
        base / "skd-dev-v1.jsonl",
        Path("configs/calibration/prompts-v1.jsonl"),
    ):
        validate_disjoint(
            prompts, [json.loads(line) for line in path.read_text("utf-8").splitlines()]
        )
    with pytest.raises(ValueError):
        validate_disjoint(prompts, [asdict(prompts[0])])


def test_bootstrap_and_spearman():
    assert paired_bootstrap([1, 2, 3]) == paired_bootstrap([1, 2, 3])
    assert paired_bootstrap([2, 2])["lower"] == paired_bootstrap([2, 2])["upper"] == 2
    assert paired_bootstrap([])["n"] == 0
    assert spearman([1, 2, 3], [3, 2, 1]) == -1
    assert spearman([1, 1, 1], [2, 3, 4]) is None
    assert analyze([], [], [])["coverage"] == []


def test_worker_rejects_extra_private_fields(monkeypatch):
    from nullmark.attacks import worker

    request = dict(
        sample=dict(sample_id="x", prompt="p", text=TEXT),
        attack="skd",
        budget=1,
        seed=7,
        model=None,
        skd=settings(),
        key_ref="should-not-pass",
    )
    output = io.StringIO()
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(request) + "\n"))
    monkeypatch.setattr("sys.stdout", output)
    worker.main()
    assert json.loads(output.getvalue()) == {"failure": "ValueError"}


def test_matched_subsets_exclude_failures_and_exhaustion_but_coverage_retains_them():
    from nullmark.evaluation.quality import quality_metrics
    from nullmark.experiments.skd import public_id

    baselines = [
        dict(sample_id=sid, scheme="kgw", before=dict(state="DETECTED", score=5.0))
        for sid in ("good", "exhausted", "failed")
    ]
    pools = [
        dict(sample_id=public_id(sid), coverage=dict(selectable=n), candidates=[])
        for sid, n in (("good", 5), ("exhausted", 2))
    ]
    rows = []
    quality = quality_metrics(TEXT, TEXT, tokenize=list)
    for baseline in baselines:
        for method in METHODS:
            for k in BUDGETS:
                failed = baseline["sample_id"] == "failed"
                rows.append(
                    {
                        **baseline,
                        "attack": method,
                        "budget": k,
                        "failure": "RuntimeError" if failed else None,
                        "after": None if failed else dict(state="DETECTED", score=4.0),
                        "outcome": "ATTACK FAILURE" if failed else "DETECTED",
                        "runtime_seconds": 1.0,
                        "quality": quality,
                        "skd": dict(
                            actual_edits=min(k, 2) if baseline["sample_id"] == "exhausted" else k,
                            selected_ids=[],
                        ),
                    }
                )
    # k=1 correlation requires candidate rows; use only k=3,5 for this accounting fixture.
    analysis = analyze(baselines, [r for r in rows if r["budget"] in (3, 5)], pools)
    coverage = next(r for r in analysis["coverage"] if r["k"] == 3)
    assert coverage["eligible"] == 3 and coverage["pool_capable"] == 1
    assert coverage["all_selectors_exact_k"] == 1 and coverage["missing_pool"] == 1
    pair = next(r for r in analysis["paired"] if r["k"] == 3)
    assert pair["n"] == 1 and pair["mean"] == 0


def test_benchmark_pipeline_saves_one_pool_and_twenty_attempts_per_eligible_sample(
    tmp_path, monkeypatch, keys
):
    import yaml

    from nullmark.experiments import skd, skd_report

    for name in ("old", "calibration", "development"):
        (tmp_path / f"{name}.jsonl").write_text(
            json.dumps(dict(id=name, style="factual", text=name)) + "\n"
        )
    (tmp_path / "fresh.jsonl").write_text(
        json.dumps(dict(id="fresh", style="factual", text="New prompt")) + "\n"
    )
    for scheme in ("kgw", "synthid"):
        (tmp_path / f"{scheme}.json").write_text("frozen fixture")
    config = dict(
        model={},
        semantic=False,
        dataset=dict(source="jsonl", path="fresh.jsonl", sample_count=1),
        calibrations={s: f"{s}.json" for s in ("kgw", "synthid")},
        baseline_prompts="old.jsonl",
        calibration_prompts="calibration.jsonl",
        development_prompts="development.jsonl",
    )
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    keys.save(tmp_path / "secrets.json")

    def generate(config_path, *, output, **kwargs):
        output.mkdir()
        for scheme in ("kgw", "synthid"):
            skd.append(
                output / "source_samples.jsonl",
                dict(sample_id=scheme + ":fresh", prompt="New prompt", text=TEXT),
            )
            skd.append(
                output / "baselines.jsonl",
                dict(
                    sample_id=scheme + ":fresh",
                    scheme=scheme,
                    style="factual",
                    seed=7,
                    before=dict(state="DETECTED", score=5.0),
                ),
            )

    def attack(self, sample, *, attack, budget, seed, skd):
        artifact = pool()
        artifact["sample_id"] = sample.sample_id
        return transform(
            sample, method=attack, k=budget, seed=seed, model=Model(), artifact=artifact
        )

    monkeypatch.setattr(skd, "verify_design", lambda x: None)
    monkeypatch.setattr(skd, "run_benchmark", generate)
    monkeypatch.setattr(
        skd,
        "resolve_model",
        lambda *a, **kw: SimpleNamespace(path=Path("public.gguf"), blob_sha256="a" * 64),
    )
    monkeypatch.setattr(skd.AttackWorker, "transform", attack)
    monkeypatch.setattr(
        skd, "load_model", lambda config: SimpleNamespace(encode=list, close=lambda: None)
    )
    monkeypatch.setattr(skd, "load_scheme", lambda *a: SimpleNamespace(detect=lambda text: None))
    monkeypatch.setattr(skd, "conditions", lambda *a: {})
    monkeypatch.setattr(skd, "require_frozen_evaluator", lambda *a, **kw: None)
    monkeypatch.setattr(
        skd.CalibratedDetector,
        "load",
        lambda p: SimpleNamespace(evaluate=lambda raw, **kw: dict(state="NOT DETECTED", score=4.0)),
    )
    monkeypatch.setattr(skd_report, "plots", lambda *a: None)
    output = skd.run_skd(
        config_path,
        output=tmp_path / "run",
        secrets_path=tmp_path / "secrets.json",
        design_commit="a" * 40,
    )
    from nullmark.experiments.runner import read_jsonl

    assert len(read_jsonl(output / "candidates/candidates.jsonl")) == 2
    assert len(read_jsonl(output / "evaluation.jsonl")) == 40
    assert json.loads((output / "manifest.json").read_text())["stage"] == "complete"
    assert (output / "summary.md").exists() and (output / "ablations.json").exists()

# Changelog

## 0.1.1 — 2026-10-20

Visual Playground (maintenance/usability insertion):

- Optional localhost FastAPI interface; bundled assets, no Node.js or cloud API.
- Cached builtin-tiny and pinned GPT-2; None, KGW and SynthID generation.
- Same-seed plain/marked comparison, divergence marker, token inspector and stepper.
- Shared typed KGW membership and SynthID depth g-values; cumulative detector traces.
- Explicit insufficient-text, retokenization and uncalibrated-score states.
- Replace direct secret fingerprints with domain-separated, master-bound HMAC references.
  Watermark key derivation stays unchanged; v0.1.0 public fingerprints require replacement.
- Regression tests, optional GUI CI and clean installation verification.
- Document pinned HF KGW repeated-n-gram counting behavior without changing the detector.

No attack algorithms were implemented. Next: **v0.2 — Baseline Attacks**.

## 0.1.0 — 2026-10-20

Reproducibility foundation:

- Installable Python package and small CLI for generation, detection, experiments and summaries.
- Open Transformers SynthID-Text and KGW-style adapters, plus CPU model inference.
- Private randomized key configurations, text-only attack boundary and explicit public exports.
- Deterministic replay, pinned pretrained model revisions and environment/dataset provenance.
- Experiment 001, paired unwatermarked controls, descriptive metrics and raw JSONL artifacts.
- Offline CPU tests, GitHub Actions, research notes and upstream attribution.

SynthID mean thresholds are uncalibrated smoke defaults. Small experiments do not
support research-scale claims. No attacks ship in 0.1.0; attack algorithms begin
in **v0.2 — Baseline Attacks**.

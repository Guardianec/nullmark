NullMark v0.1.0 establishes the reproducibility foundation for controlled research
on open generative-text watermarks.

- Local causal model adapter with pinned GPT-2 support and an offline CPU smoke model.
- Transformers reference SynthID-Text generation and mean scoring, plus KGW-style generation/detection.
- Multiple private key configurations, text-only attack inputs, separated evaluator artifacts.
- Config-driven Experiment 001, paired plain controls, deterministic replay, descriptive metrics and JSONL.
- Automated tests, CPU CI, research-design notes and license attribution.

Smoke results are not research-scale evidence. SynthID thresholds are uncalibrated;
no production or proprietary watermark system is queried.

**Attack algorithms begin in v0.2 — Baseline Attacks. No attack algorithms are included in v0.1.0.**

# NullMark v0.2.0 — Baseline Attacks

Four keyless, detector-blind baselines now run through an isolated text-only
subprocess: Random Edit, contextual Local Replacement, one-pass Paraphrase and
ordinary-entropy Rewrite. A fresh 240-prompt corpus, unchanged frozen evaluators,
continuous preservation metrics, quality-conditioned accounting, static plots and
a before/diff/after Playground make the disruption-versus-damage tradeoff visible.

The installed Qwen run used 128 eligible originals per scheme and completed all
4,096 attempts. Paraphrase evasion was 2/128 KGW and 7/128 SynthID, with separate
29/128 and 32/128 post-attack abstentions. Sparse attacks had no observed evasion
and exhausted safe candidates at mean actual editing below 1%; this does not
establish robustness at 20% actual editing. Semantic similarity is not factual
correctness. Target FPR 1% remains distinct from the prior SynthID observed
held-out 3.03% FPR.

[Full measured results](baseline-attack-results.md) ·
[Methodology](baseline-attacks.md) · [Verification](release-verification.md).

v0.3 Sparse Keyless Disruption has NOT been started.

---

NullMark v0.1.1 adds the **Visual Playground**, a local interactive view of the
existing watermark generation and detection pipeline.

- Optional FastAPI/Uvicorn interface with bundled assets and localhost defaults.
- Offline builtin-tiny, pinned GPT-2 and optional supported Ollama-installed GGUFs.
- Direct native inference with exact IDs, embedded chat formatting and real per-token HF watermark hooks.
- Visible temperature/top-k/top-p controls; historical Experiment 001 retains its original settings.
- Local model capability diagnostic and Windows Qwen 3.5 9B validation without duplicate weights.
- Same-seed plain/marked comparison, first divergence, token inspector and stepper.
- KGW context-aware membership and cumulative detector z-score traces.
- SynthID per-depth g-values and cumulative mean-g, explicitly uncalibrated.
- Shared typed inspection; short-text and retokenization handling.
- Master-bound HMAC references replace guessable direct-secret hashes.
  Key derivation stays unchanged; old fingerprints require replacement.
- Core/GUI regression tests, optional GUI CI and clean-install verification.

```sh
pip install -e ".[gui]"
nullmark playground
```

The CLI remains authoritative for reproducible experiments. The GUI is trusted
local exploration tooling. Detector scores are not proof of authorship; SynthID
has no calibrated false-positive rate. Pinned HF KGW repeated-n-gram counting
behavior is documented and preserved. No generation-time probabilities are fabricated.

**No attack algorithms were implemented. Next: v0.2 — Baseline Attacks.**
